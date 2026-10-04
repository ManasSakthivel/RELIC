"""
Program semantics for the JCL oracle.

For every executed step the oracle needs to know which datasets the program
reads and writes and, for IDCAMS, which catalog operations it performs.
Programs are classified as:

* modelled utilities (IEFBR14, IEBGENER, SORT, IEBCOPY, IDCAMS, the COBOL
  compiler and binder) — semantics from the IBM utility documentation;
* COBOL programs whose source is available in the subject system — file
  access derived from ``SELECT ... ASSIGN TO`` and ``OPEN`` statements;
* everything else — *opaque*: the oracle falls back to DD dispositions
  (NEW/MOD -> write, OLD -> read+write, SHR -> read) and flags the step, so
  that an equivalence verdict that depends on it becomes UNDETERMINED.

A COBOL program that also contains ``EXEC SQL`` / ``EXEC CICS`` /
``EXEC DLI`` / ``CBLTDLI`` / MQ calls is file-modelled but flagged opaque,
because it has side effects outside the datasets named in the JCL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from jcl_oracle.model import DD, Step


@dataclass
class Access:
    ddname: str
    mode: str                 # "R", "W" or "RW"


@dataclass
class CatalogOp:
    """A catalog-level operation performed by IDCAMS (by dataset name)."""
    verb: str                 # DELETE, DEFINE, READ, WRITE, RENAME, SETCC,
                              # FILE_R / FILE_W (access through a DD name),
                              # IFSET (IF LASTCC|MAXCC op n THEN SET ... = m)
    name: str = ""
    other: str = ""           # RELATE/PATHENTRY target, rename target
    value: int = 0            # SETCC value
    kind: str = ""            # SETCC kind: MAXCC or LASTCC


@dataclass
class ProgramEffect:
    accesses: list[Access] = field(default_factory=list)
    catalog_ops: list[CatalogOp] = field(default_factory=list)
    opaque_reasons: list[str] = field(default_factory=list)
    reads_program_library: bool = True


# ---------------------------------------------------------------------------
# COBOL source analysis
# ---------------------------------------------------------------------------

@dataclass
class CobolInfo:
    dd_modes: dict[str, str]
    opaque_reasons: list[str]


_OPAQUE_COBOL = [
    (re.compile(r"\bEXEC\s+SQL\b", re.I), "EXEC SQL (DB2)"),
    (re.compile(r"\bEXEC\s+CICS\b", re.I), "EXEC CICS"),
    (re.compile(r"\bEXEC\s+DLI\b", re.I), "EXEC DLI (IMS)"),
    (re.compile(r"CBLTDLI|AIBTDLI", re.I), "IMS DL/I call"),
    (re.compile(r"\bMQ(OPEN|PUT|GET|CONN)\b", re.I), "MQ call"),
]


def _cobol_code(text: str) -> str:
    """Strip sequence area, indicator-column comments and identification area."""
    out = []
    for line in text.splitlines():
        if len(line) >= 7 and line[6] in "*/":
            continue
        out.append(line[7:72] if len(line) > 7 else "")
    return "\n".join(out)


def analyse_cobol(text: str) -> CobolInfo:
    code = _cobol_code(text)
    flat = re.sub(r"\s+", " ", code.upper())
    selects: dict[str, str] = {}
    for m in re.finditer(r"\bSELECT\s+(?:OPTIONAL\s+)?([A-Z0-9-]+)\s+ASSIGN\s+(?:TO\s+)?([A-Z0-9'@#$-]+|USING\s+[A-Z0-9-]+)", flat):
        fname, target = m.group(1), m.group(2)
        if target.startswith("USING"):
            selects[fname] = "?DYNAMIC"
            continue
        target = target.strip("'")
        # UT-S-DDNAME / S-DDNAME / DA-...-DDNAME -> last component is the DD name
        dd = target.split("-")[-1]
        selects[fname] = dd
    modes: dict[str, set[str]] = {}
    for m in re.finditer(r"\bOPEN\s+((?:(?:INPUT|OUTPUT|I-O|EXTEND)\s+(?:[A-Z0-9-]+\s*)+)+)", flat):
        clause = m.group(1)
        current = None
        for tok in clause.split():
            if tok in {"INPUT", "OUTPUT", "I-O", "EXTEND"}:
                current = tok
                continue
            if current and tok in selects:
                modes.setdefault(tok, set()).add(current)
    opaque = [why for rx, why in _OPAQUE_COBOL if rx.search(code)]
    dd_modes: dict[str, str] = {}
    for fname, dd in selects.items():
        if dd == "?DYNAMIC":
            opaque.append(f"dynamic file assignment ({fname})")
            continue
        ms = modes.get(fname, set())
        if not ms:
            continue
        read = bool(ms & {"INPUT", "I-O", "EXTEND"})
        write = bool(ms & {"OUTPUT", "I-O", "EXTEND"})
        mode = "RW" if read and write else ("R" if read else "W")
        prev = dd_modes.get(dd)
        if prev and prev != mode:
            mode = "RW"
        dd_modes[dd] = mode
    return CobolInfo(dd_modes=dd_modes, opaque_reasons=sorted(set(opaque)))


# ---------------------------------------------------------------------------
# IDCAMS
# ---------------------------------------------------------------------------

def _idcams_commands(lines: list[str]) -> list[str]:
    """Join IDCAMS control statements into commands (handles '-'/'+' continuation
    and /* */ comments)."""
    text_lines = []
    for raw in lines:
        line = raw[:72]
        text_lines.append(line)
    text = "\n".join(text_lines)
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    cmds: list[str] = []
    cur = ""
    for line in text.splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        if s.endswith("-") or s.endswith("+"):
            cur += " " + s[:-1]
            continue
        cur += " " + s
        cmds.append(" ".join(cur.split()))
        cur = ""
    if cur.strip():
        cmds.append(" ".join(cur.split()))
    # A single line may hold several commands separated by ';'
    out: list[str] = []
    for c in cmds:
        out.extend(p.strip() for p in c.split(";") if p.strip())
    return out


def _paren_arg(cmd: str, key: str) -> str | None:
    m = re.search(rf"\b{key}\s*\(\s*([^()\s]+(?:\([^()\s]*\))?)", cmd, re.I)
    return m.group(1).upper().strip("'") if m else None


def idcams_effect(step: Step) -> ProgramEffect:
    eff = ProgramEffect(reads_program_library=False)
    sysin = step.dds.get("SYSIN")
    if sysin is None:
        eff.opaque_reasons.append("IDCAMS without SYSIN")
        return eff
    if not sysin.instream:
        if sysin.refs:
            eff.opaque_reasons.append("IDCAMS commands read from a dataset")
            eff.accesses.append(Access("SYSIN", "R"))
        return eff
    for cmd in _idcams_commands(sysin.instream):
        u = cmd.upper()
        verb = u.split()[0] if u.split() else ""
        if verb in {"DELETE", "DEL"}:
            rest = u.split(None, 1)[1] if len(u.split(None, 1)) > 1 else ""
            m = re.match(r"\(?\s*([A-Z0-9@#$.&<>_-]+(?:\([^)]*\))?)", rest)
            if not m:
                eff.opaque_reasons.append(f"unparsed IDCAMS: {cmd[:40]}")
                continue
            name = m.group(1)
            if "*" in name or "%" in name:
                eff.opaque_reasons.append("IDCAMS generic DELETE")
                continue
            eff.catalog_ops.append(CatalogOp("DELETE", name))
        elif verb in {"DEFINE", "DEF"}:
            name = _paren_arg(u, "NAME")
            if not name:
                eff.opaque_reasons.append(f"unparsed IDCAMS: {cmd[:40]}")
                continue
            other = _paren_arg(u, "RELATE") or _paren_arg(u, "PATHENTRY") or ""
            eff.catalog_ops.append(CatalogOp("DEFINE", name, other=other))
        elif verb in {"REPRO", "BLDINDEX", "BIX"}:
            src = _paren_arg(u, "INFILE") or _paren_arg(u, "IFILE")
            srcds = _paren_arg(u, "INDATASET") or _paren_arg(u, "IDS")
            dst = _paren_arg(u, "OUTFILE") or _paren_arg(u, "OFILE")
            dstds = _paren_arg(u, "OUTDATASET") or _paren_arg(u, "ODS")
            if not (src or srcds) or not (dst or dstds):
                eff.opaque_reasons.append(f"unparsed IDCAMS: {cmd[:40]}")
                continue
            if src:
                eff.catalog_ops.append(CatalogOp("FILE_R", src))
            else:
                eff.catalog_ops.append(CatalogOp("READ", srcds or ""))
            if dst:
                eff.catalog_ops.append(CatalogOp("FILE_W", dst))
            else:
                eff.catalog_ops.append(CatalogOp("WRITE", dstds or ""))
        elif verb in {"PRINT", "VERIFY", "EXAMINE"}:
            f = _paren_arg(u, "INFILE") or _paren_arg(u, "FILE")
            ds = _paren_arg(u, "INDATASET") or _paren_arg(u, "DATASET") or _paren_arg(u, "NAME")
            if f:
                eff.catalog_ops.append(CatalogOp("FILE_R", f))
            elif ds:
                eff.catalog_ops.append(CatalogOp("READ", ds))
            else:
                eff.opaque_reasons.append(f"unparsed IDCAMS: {cmd[:40]}")
        elif verb in {"LISTCAT", "LISTC"}:
            ent = _paren_arg(u, "ENTRIES") or _paren_arg(u, "ENT")
            if ent:
                eff.catalog_ops.append(CatalogOp("READ", ent))
        elif verb == "ALTER":
            parts = u.split()
            name = parts[1].strip("()") if len(parts) > 1 else ""
            newname = _paren_arg(u, "NEWNAME")
            if newname:
                eff.catalog_ops.append(CatalogOp("RENAME", name, other=newname))
            elif name:
                eff.catalog_ops.append(CatalogOp("READ", name))
                eff.catalog_ops.append(CatalogOp("WRITE", name))
        elif verb == "SET":
            m = re.match(r"SET\s+(MAXCC|LASTCC)\s*=\s*(\d+)", u)
            if m:
                eff.catalog_ops.append(CatalogOp("SETCC", kind=m.group(1), value=int(m.group(2))))
            else:
                eff.opaque_reasons.append(f"unparsed IDCAMS: {cmd[:40]}")
        elif verb == "IF":
            # Only the conditional-reset form is modelled:
            #   IF LASTCC|MAXCC op n THEN SET LASTCC|MAXCC = m
            m = re.match(r"IF\s+(LASTCC|MAXCC)\s*(=|EQ|NE|¬=|GT|>|GE|>=|LT|<|LE|<=)\s*(\d+)\s+"
                         r"THEN\s+SET\s+(MAXCC|LASTCC)\s*=\s*(\d+)\s*$", u)
            if m:
                eff.catalog_ops.append(CatalogOp(
                    "IFSET", name=f"{m.group(1)}|{_IDC_OPS[m.group(2)]}|{m.group(3)}",
                    kind=m.group(4), value=int(m.group(5))))
            else:
                eff.opaque_reasons.append(f"IDCAMS modal command not modelled: {cmd[:40]}")
        else:
            eff.opaque_reasons.append(f"IDCAMS command not modelled: {verb}")
    return eff


_IDC_OPS = {"=": "EQ", "EQ": "EQ", "NE": "NE", "¬=": "NE", "GT": "GT", ">": "GT",
            "GE": "GE", ">=": "GE", "LT": "LT", "<": "LT", "LE": "LE", "<=": "LE"}


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _dd_names(step: Step) -> list[str]:
    return [d.split(".")[-1] for d in step.dds]


def _sort_effect(step: Step) -> ProgramEffect:
    eff = ProgramEffect()
    for dd in _dd_names(step):
        if dd == "SORTIN" or re.fullmatch(r"SORTIN\d\d", dd) or dd in {"SORTJNF1", "SORTJNF2"}:
            eff.accesses.append(Access(dd, "R"))
        elif dd == "SORTOUT" or re.fullmatch(r"SORTOF\w{1,2}", dd):
            eff.accesses.append(Access(dd, "W"))
    sysin = step.dds.get("SYSIN")
    if sysin is not None:
        text = " ".join(sysin.instream).upper()
        for m in re.finditer(r"FNAMES=\(?([A-Z0-9@#$,]+)\)?", text):
            for name in m.group(1).split(","):
                if name:
                    eff.accesses.append(Access(name, "W"))
        if sysin.refs:
            eff.accesses.append(Access("SYSIN", "R"))
    return eff


def _iebcopy_effect(step: Step) -> ProgramEffect:
    eff = ProgramEffect()
    sysin = step.dds.get("SYSIN")
    text = " ".join(sysin.instream).upper() if sysin else ""
    found = False
    for m in re.finditer(r"\b(?:COPY|C)\s+((?:[A-Z]+=\(?[A-Z0-9@#$,()]+\)?,?\s*)+)", text):
        args = m.group(1)
        out = re.search(r"\b(?:OUTDD|O)=([A-Z0-9@#$]+)", args)
        ins = re.search(r"\b(?:INDD|I)=\(?([A-Z0-9@#$,]+)\)?", args)
        if out and ins:
            found = True
            eff.accesses.append(Access(out.group(1), "W"))
            for n in ins.group(1).split(","):
                if n:
                    eff.accesses.append(Access(n, "R"))
    if not found:
        if "SYSUT1" in step.dds and "SYSUT2" in step.dds:
            eff.accesses += [Access("SYSUT1", "R"), Access("SYSUT2", "W")]
        else:
            eff.opaque_reasons.append("IEBCOPY control statements not modelled")
    return eff


_OPAQUE_PROGRAMS = {
    "IKJEFT01": "TSO batch (arbitrary commands / DB2 DSN)",
    "IKJEFT1A": "TSO batch (arbitrary commands / DB2 DSN)",
    "IKJEFT1B": "TSO batch (arbitrary commands / DB2 DSN)",
    "SDSF": "SDSF batch (operator commands)",
    "ISFAFD": "SDSF batch (operator commands)",
    "DFSRRC00": "IMS region controller",
    "FTP": "FTP client (network side effects)",
    "DFHCSDUP": "CICS CSD utility",
    "DSNUTILB": "DB2 utility",
    "DSNTIAD": "DB2 dynamic SQL",
    "DSNTEP2": "DB2 dynamic SQL",
    "IRXJCL": "REXX",
    "BPXBATCH": "z/OS UNIX shell",
    "IEBUPDTE": "IEBUPDTE control statements",
    "ADRDSSU": "DFSMSdss",
    "IEHPROGM": "IEHPROGM catalog utility",
}


def program_effect(step: Step, cobol_sources: dict[str, str] | None = None) -> ProgramEffect:
    """Return the modelled effect of the program run by *step*."""
    cobol_sources = cobol_sources or {}
    if step.proc_unexpanded is not None:
        eff = _disp_fallback(step)
        eff.opaque_reasons.append(f"procedure {step.proc_unexpanded} not available")
        return eff
    pgm = (step.pgm or "").upper()
    if pgm.startswith("*."):
        # Program loaded from a dataset created earlier in the job (e.g. the
        # GO step of compile-link-go): user code, side effects unknown.
        eff = _disp_fallback(step)
        eff.opaque_reasons.append("user program loaded via referback")
        eff.reads_program_library = False
        return eff
    if pgm == "IEFBR14":
        return ProgramEffect(reads_program_library=False)
    if pgm in {"IEBGENER", "ICEGENER"}:
        return ProgramEffect([Access("SYSUT1", "R"), Access("SYSUT2", "W")])
    if pgm in {"SORT", "ICEMAN", "DFSORT", "SYNCSORT", "ICETOOL"}:
        eff = _sort_effect(step)
        if pgm == "ICETOOL":
            eff.opaque_reasons.append("ICETOOL operators not modelled")
        return eff
    if pgm == "IEBCOPY":
        return _iebcopy_effect(step)
    if pgm == "IDCAMS":
        return idcams_effect(step)
    if pgm in {"IGYCRCTL", "IGYWC"}:
        return ProgramEffect([Access("SYSIN", "R"), Access("SYSLIB", "R"), Access("SYSLIN", "W")])
    if pgm in {"IEWL", "IEWBLINK", "HEWL", "HEWLH096", "IEWBLDGO"}:
        return ProgramEffect([Access("SYSLIN", "R"), Access("SYSLIB", "R"), Access("SYSLMOD", "W")])
    if pgm in _OPAQUE_PROGRAMS:
        eff = _disp_fallback(step)
        eff.opaque_reasons.append(_OPAQUE_PROGRAMS[pgm])
        return eff
    src = cobol_sources.get(pgm)
    if src is not None:
        info = analyse_cobol(src)
        eff = ProgramEffect([Access(dd, mode) for dd, mode in sorted(info.dd_modes.items())])
        eff.opaque_reasons.extend(info.opaque_reasons)
        return eff
    eff = _disp_fallback(step)
    eff.opaque_reasons.append(f"program {pgm or '?'} source not available")
    return eff


def _disp_fallback(step: Step) -> ProgramEffect:
    eff = ProgramEffect()
    for name, dd in step.dds.items():
        if not dd.refs:
            continue
        status = dd.refs[0].status
        mode = {"NEW": "W", "MOD": "RW", "OLD": "RW", "SHR": "R"}.get(status, "R")
        eff.accesses.append(Access(name.split(".")[-1], mode))
    return eff


def dd_for(step: Step, ddname: str) -> DD | None:
    if ddname in step.dds:
        return step.dds[ddname]
    for k, v in step.dds.items():
        if k.split(".")[-1] == ddname:
            return v
    return None

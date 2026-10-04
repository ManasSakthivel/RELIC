"""
Statement model for the JCL oracle: jobs, steps, DDs, IF/THEN/ELSE blocks,
symbolic parameters and PROC expansion.

Independent of RELIC: this module reads only ``jcl_oracle.lexer`` output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Union

from jcl_oracle.lexer import Statement, lex, parse_operands, split_top, unparen

# EXEC keywords that are not symbolic-parameter overrides.
_EXEC_SYSTEM_KEYWORDS = {
    "PGM", "PROC", "COND", "PARM", "TIME", "REGION", "ACCT", "ADDRSPC",
    "DPRTY", "DYNAMNBR", "PERFORM", "RD", "CCSID", "MEMLIMIT", "RLSTMOUT",
    "PARMDD", "TVSMSG", "TVSAMCOM",
}

_SYMBOL_RE = re.compile(r"(?<!&)&([A-Z@#$][A-Z0-9@#$]{0,7})(\.?)", re.I)


def substitute(text: str, symbols: dict[str, str]) -> str:
    """Replace &NAME / &NAME. with symbol values; leave unknown symbols and &&temp."""
    def repl(m: re.Match[str]) -> str:
        key = m.group(1).upper()
        if key in symbols:
            return symbols[key]
        return m.group(0)
    prev = None
    out = text
    # Symbols may expand to text containing further symbols (bounded).
    for _ in range(4):
        prev = out
        out = _SYMBOL_RE.sub(repl, out)
        if out == prev:
            break
    return out


def _strip_quotes(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == "'" and v[-1] == "'":
        return v[1:-1].replace("''", "'")
    return v


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DSRef:
    """One dataset reference within a DD (DDs may concatenate several)."""
    key: str                 # normalised dataset name incl. (member) / (gen)
    status: str = "OLD"      # NEW, OLD, SHR, MOD
    normal: str = ""         # normal-termination disposition ("" = default)
    abnormal: str = ""       # abnormal-termination disposition ("" = same as normal)

    @property
    def temporary(self) -> bool:
        return self.key.startswith("&&")


@dataclass
class DD:
    ddname: str
    refs: list[DSRef] = field(default_factory=list)
    sysout: bool = False
    dummy: bool = False
    instream: list[str] = field(default_factory=list)
    referback: str = ""      # raw '*.STEP.DD' value if unresolved
    keywords: dict[str, str] = field(default_factory=dict)
    positional: list[str] = field(default_factory=list)


@dataclass
class Step:
    name: str                       # step name as written ("" if unnamed)
    ident: str = ""                 # unique identity within the file
    top_name: str = ""              # invoking job-step name (for proc steps)
    pgm: str | None = None
    proc_unexpanded: str | None = None  # proc invoked but not found -> opaque
    cond: str | None = None
    parm: str = ""
    dds: dict[str, DD] = field(default_factory=dict)
    first_line: int = -1            # physical line span of the job-level EXEC block
    last_line: int = -1
    proc_prefix: str = ""           # "STEP." for steps expanded from a proc


@dataclass
class IfBlock:
    expr: str
    then_items: list["Item"] = field(default_factory=list)
    else_items: list["Item"] = field(default_factory=list)
    has_else: bool = False


Item = Union[Step, IfBlock]


@dataclass
class Job:
    name: str
    items: list[Item] = field(default_factory=list)
    cond: str | None = None
    joblib: list[DSRef] = field(default_factory=list)


@dataclass
class FileModel:
    jobs: list[Job] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def steps(self) -> list[Step]:
        out: list[Step] = []
        for job in self.jobs:
            out.extend(iter_steps(job.items))
        return out


def iter_steps(items: list[Item]) -> list[Step]:
    out: list[Step] = []
    for it in items:
        if isinstance(it, Step):
            out.append(it)
        else:
            out.extend(iter_steps(it.then_items))
            out.extend(iter_steps(it.else_items))
    return out


# ---------------------------------------------------------------------------
# PROC library
# ---------------------------------------------------------------------------

@dataclass
class ProcDef:
    name: str
    defaults: dict[str, str]
    body: list[Statement]


class ProcLibrary:
    """Cataloged procedures available to a subject system (by member/proc name)."""

    def __init__(self) -> None:
        self.procs: dict[str, ProcDef] = {}

    @classmethod
    def from_texts(cls, texts: dict[str, str]) -> "ProcLibrary":
        """texts: member name -> source text. Files that define a PROC are indexed
        both by the PROC statement name and by the member name."""
        lib = cls()
        for member, text in texts.items():
            stmts = lex(text)
            for idx, st in enumerate(stmts):
                if st.kind == "STMT" and st.op == "PROC":
                    if any(s.kind == "STMT" and s.op == "JOB" for s in stmts[:idx]):
                        break  # in-stream proc inside a job: handled per file
                    body: list[Statement] = []
                    for s in stmts[idx + 1:]:
                        if s.kind == "STMT" and s.op == "PEND":
                            break
                        body.append(s)
                    _, kw = parse_operands(st.operands)
                    defaults = {k: _strip_quotes(v) for k, v in kw.items()}
                    pd = ProcDef(st.name or member.upper(), defaults, body)
                    lib.procs.setdefault(pd.name.upper(), pd)
                    lib.procs.setdefault(member.upper(), pd)
                    break
        return lib

    def get(self, name: str) -> ProcDef | None:
        return self.procs.get(name.upper())


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def _parse_disp(value: str | None, default_status: str = "NEW") -> tuple[str, str, str]:
    if value is None:
        return default_status, "", ""
    parts = split_top(unparen(value))
    status = (parts[0] or default_status).upper() if parts else default_status
    normal = parts[1].upper() if len(parts) > 1 else ""
    abnormal = parts[2].upper() if len(parts) > 2 else ""
    return status, normal, abnormal


def normalise_dsn(dsn: str) -> str:
    return _strip_quotes(dsn).upper().replace(" ", "")


class _Builder:
    def __init__(self, stmts: list[Statement], proclib: ProcLibrary | None):
        self.stmts = stmts
        self.proclib = proclib or ProcLibrary()
        self.model = FileModel()
        self.instream_procs: dict[str, ProcDef] = {}

    # -- DD construction ---------------------------------------------------

    def make_dd(self, st: Statement, ddname: str, symbols: dict[str, str]) -> DD:
        operands = substitute(st.operands, symbols)
        positional, kw = parse_operands(operands)
        dd = DD(ddname=ddname, keywords=kw, positional=[p.upper() for p in positional])
        pos0 = dd.positional[0] if dd.positional else ""
        if pos0 in {"*", "DATA"}:
            dd.instream = list(st.data)
        if pos0 == "DUMMY":
            dd.dummy = True
        if "SYSOUT" in kw:
            dd.sysout = True
        dsn = kw.get("DSN", kw.get("DSNAME"))
        if dsn is not None:
            key = normalise_dsn(dsn)
            if key == "NULLFILE":
                dd.dummy = True
            elif key.startswith("*."):
                dd.referback = key
            else:
                default = "NEW"
                status, normal, abnormal = _parse_disp(kw.get("DISP"), default)
                dd.refs.append(DSRef(key, status, normal, abnormal))
        return dd

    # -- Statement walking -------------------------------------------------

    def build(self) -> FileModel:
        stmts = self.stmts
        i = 0
        job: Job | None = None
        symbols: dict[str, str] = {}
        stack: list[tuple[IfBlock, bool]] = []  # (block, in_else)
        current_step: Step | None = None
        last_dd: DD | None = None
        pending_overrides: list[tuple[Statement, str, str]] = []
        proc_invocation: dict | None = None
        unnamed = 0

        def target_list() -> list[Item]:
            assert job is not None
            if stack:
                blk, in_else = stack[-1]
                return blk.else_items if in_else else blk.then_items
            return job.items

        def finish_invocation() -> None:
            nonlocal proc_invocation
            if proc_invocation is not None:
                self._expand_invocation(proc_invocation, pending_overrides)
                proc_invocation = None
            pending_overrides.clear()

        while i < len(stmts):
            st = stmts[i]
            i += 1
            if st.kind != "STMT":
                if st.kind == "NULL" and job is not None:
                    finish_invocation()
                    if stack:
                        self.model.errors.append("IF without ENDIF at end of job")
                        stack.clear()
                    job = None
                    current_step = None
                continue
            op = st.op
            if op == "JOB":
                finish_invocation()
                if stack:
                    self.model.errors.append("IF without ENDIF before next JOB")
                    stack.clear()
                _, kw = parse_operands(st.operands)
                job = Job(name=st.name or f"JOB{len(self.model.jobs) + 1}",
                          cond=kw.get("COND"))
                self.model.jobs.append(job)
                symbols = {}
                current_step = None
                continue
            if op == "PROC":
                # In-stream procedure definition (or a proc member without a JOB).
                body: list[Statement] = []
                while i < len(stmts):
                    s = stmts[i]
                    i += 1
                    if s.kind == "STMT" and s.op == "PEND":
                        break
                    body.append(s)
                _, kw = parse_operands(st.operands)
                self.instream_procs[(st.name or "").upper()] = ProcDef(
                    st.name, {k: _strip_quotes(v) for k, v in kw.items()}, body)
                continue
            if job is None:
                if op in {"EXEC", "DD"}:
                    self.model.notes.append(f"statement outside job at line {st.first_line + 1}")
                continue
            if op == "SET":
                _, kw = parse_operands(substitute(st.operands, symbols))
                for k, v in kw.items():
                    symbols[k.upper()] = _strip_quotes(v)
                continue
            if op == "IF":
                finish_invocation()
                blk = IfBlock(expr=substitute(st.operands, symbols))
                target_list().append(blk)
                stack.append((blk, False))
                current_step = None
                continue
            if op == "ELSE":
                finish_invocation()
                if not stack:
                    self.model.errors.append(f"ELSE without IF at line {st.first_line + 1}")
                else:
                    blk, _ = stack.pop()
                    blk.has_else = True
                    stack.append((blk, True))
                current_step = None
                continue
            if op == "ENDIF":
                finish_invocation()
                if not stack:
                    self.model.errors.append(f"ENDIF without IF at line {st.first_line + 1}")
                else:
                    stack.pop()
                current_step = None
                continue
            if op == "EXEC":
                finish_invocation()
                operands = substitute(st.operands, symbols)
                positional, kw = parse_operands(operands)
                name = st.name
                if not name:
                    unnamed += 1
                step = Step(name=name, top_name=name, first_line=st.first_line,
                            last_line=st.end_line, cond=kw.get("COND"),
                            parm=kw.get("PARM", ""))
                if "PGM" in kw:
                    step.pgm = kw["PGM"].upper()
                    target_list().append(step)
                    current_step = step
                    last_dd = None
                else:
                    proc_name = (kw.get("PROC") or (positional[0] if positional else "")).upper()
                    proc_invocation = {
                        "name": proc_name, "step": step, "kw": kw,
                        "target": target_list(), "symbols": dict(symbols),
                    }
                    current_step = step
                    last_dd = None
                continue
            if op == "DD":
                if current_step is None:
                    # JOBLIB / JCLLIB-level DDs before the first step.
                    if st.name == "JOBLIB":
                        dd = self.make_dd(st, "JOBLIB", symbols)
                        job.joblib.extend(dd.refs)
                    continue
                if proc_invocation is not None:
                    pending_overrides.append((st, st.name, substitute(st.operands, symbols)))
                    continue
                if st.name:
                    dd = self.make_dd(st, st.name, symbols)
                    current_step.dds[st.name] = dd
                    last_dd = dd
                elif last_dd is not None:
                    extra = self.make_dd(st, last_dd.ddname, symbols)
                    last_dd.refs.extend(extra.refs)        # concatenation
                    last_dd.instream.extend(extra.instream)
                continue
            # Other statements (JCLLIB, INCLUDE, OUTPUT, ...) have no step semantics
            # that the oracle models.
            if op == "INCLUDE":
                self.model.notes.append(f"INCLUDE not expanded at line {st.first_line + 1}")
            continue

        finish_invocation()
        if stack:
            self.model.errors.append("IF without ENDIF at end of file")
        self._assign_idents()
        self._resolve_referbacks()
        return self.model

    # -- PROC expansion -------------------------------------------------------

    def _expand_invocation(self, inv: dict, overrides: list[tuple[Statement, str, str]],
                           depth: int = 0) -> None:
        step: Step = inv["step"]
        target: list[Item] = inv["target"]
        name = inv["name"]
        pdef = self.instream_procs.get(name) or self.proclib.get(name)
        if pdef is None or depth > 3:
            # Unknown procedure: opaque single step; overrides attach to it.
            step.proc_unexpanded = name or "?"
            for st, dname, _ops in overrides:
                ddname = dname.split(".")[-1] if dname else ""
                if ddname:
                    dd = self.make_dd(st, dname, inv["symbols"])
                    step.dds[dname] = dd
            target.append(step)
            return

        params = dict(pdef.defaults)
        exec_kw: dict[str, str] = inv["kw"]
        cond_all = exec_kw.get("COND")
        cond_per: dict[str, str] = {}
        for k, v in exec_kw.items():
            if "." in k:
                base, ps = k.split(".", 1)
                if base == "COND":
                    cond_per[ps.upper()] = v
                continue
            if k not in _EXEC_SYSTEM_KEYWORDS:
                params[k.upper()] = _strip_quotes(v)
        symbols = dict(inv["symbols"])
        symbols.update(params)

        override_map: dict[str, list[tuple[Statement, str]]] = {}
        first_ps: str | None = None
        for s in pdef.body:
            if s.kind == "STMT" and s.op == "EXEC":
                first_ps = s.name.upper()
                break
        for st, dname, _ops in overrides:
            if "." in dname:
                ps, ddn = dname.split(".", 1)
            else:
                ps, ddn = (first_ps or ""), dname
            override_map.setdefault(ps.upper(), []).append((st, ddn.upper()))

        prefix = (step.name or name) + "."
        cur: Step | None = None
        last_dd: DD | None = None
        expanded: list[Step] = []
        for s in pdef.body:
            if s.kind != "STMT":
                continue
            if s.op == "EXEC":
                ops = substitute(s.operands, symbols)
                positional, kw = parse_operands(ops)
                ps_name = s.name.upper()
                cond = kw.get("COND")
                if cond_all is not None:
                    cond = cond_all
                if ps_name in cond_per:
                    cond = cond_per[ps_name]
                cur = Step(name=prefix + ps_name, top_name=step.name, cond=cond,
                           parm=kw.get("PARM", ""), first_line=step.first_line,
                           last_line=step.last_line, proc_prefix=prefix)
                if "PGM" in kw:
                    cur.pgm = kw["PGM"].upper()
                else:
                    cur.proc_unexpanded = (kw.get("PROC") or (positional[0] if positional else "?")).upper()
                expanded.append(cur)
                last_dd = None
                continue
            if s.op == "DD" and cur is not None:
                if s.name:
                    dd = self.make_dd(s, s.name, symbols)
                    cur.dds[s.name] = dd
                    last_dd = dd
                elif last_dd is not None:
                    extra = self.make_dd(s, last_dd.ddname, symbols)
                    last_dd.refs.extend(extra.refs)
        # Apply overrides (parameter-level merge with the procedure DD).
        for ps_step in expanded:
            ps = ps_step.name[len(prefix):]
            for st, ddn in override_map.get(ps, []):
                ov = self.make_dd(st, ddn, inv["symbols"])
                base = ps_step.dds.get(ddn)
                if base is None:
                    ps_step.dds[ddn] = ov
                else:
                    merged_kw = dict(base.keywords)
                    merged_kw.update(ov.keywords)
                    merged_pos = ov.positional or base.positional
                    text = ",".join(merged_pos + [f"{k}={v}" for k, v in merged_kw.items()])
                    fake = Statement("STMT", name=ddn, op="DD", operands=text,
                                     data=ov.instream or base.instream)
                    ps_step.dds[ddn] = self.make_dd(fake, ddn, {})
        target.extend(expanded)

    # -- Identities ------------------------------------------------------------

    def _assign_idents(self) -> None:
        """
        Step identity used to compare two versions of a file.

        A uniquely named step is identified by its name. Steps that share a name
        are identified by name + a hash of their content (program/procedure,
        PARM, DD statements, in-stream data; COND is excluded so that a guard
        change does not change identity). Purely positional identities would
        make a swap of two same-named but different steps invisible.
        Identical same-named steps (true duplicates) get an occurrence suffix.
        """
        import hashlib

        steps = self.model.steps()
        counts: dict[str, int] = {}
        for i, st in enumerate(steps, 1):
            base = st.name or f"#{i}"
            counts[base] = counts.get(base, 0) + 1
        used: dict[str, int] = {}
        for i, st in enumerate(steps, 1):
            base = st.name or f"#{i}"
            if counts[base] == 1:
                ident = base
            else:
                sig = repr((st.pgm, st.proc_unexpanded, st.parm, sorted(
                    (n, tuple((r.key, r.status, r.normal, r.abnormal) for r in d.refs),
                     d.sysout, d.dummy, tuple(d.instream)) for n, d in st.dds.items())))
                ident = f"{base}~{hashlib.sha256(sig.encode()).hexdigest()[:8]}"
            k = used.get(ident, 0) + 1
            used[ident] = k
            st.ident = ident if k == 1 else f"{ident}#{k}"

    def _resolve_referbacks(self) -> None:
        for job in self.model.jobs:
            by_name: dict[str, Step] = {}
            for st in iter_steps(job.items):
                for dd in st.dds.values():
                    if dd.referback:
                        parts = dd.referback[2:].split(".")
                        src = None
                        if len(parts) == 1:
                            src = st.dds.get(parts[0])
                        elif len(parts) >= 2:
                            ref_step = by_name.get(parts[0]) or by_name.get(".".join(parts[:-1]))
                            if ref_step is not None:
                                src = ref_step.dds.get(parts[-1])
                        if src is not None and src.refs:
                            status, normal, abnormal = _parse_disp(dd.keywords.get("DISP"), "OLD")
                            dd.refs.append(DSRef(src.refs[0].key, status, normal, abnormal))
                        else:
                            self.model.notes.append(f"unresolved referback {dd.referback}")
                by_name[st.name] = st


def build_model(text: str, proclib: ProcLibrary | None = None) -> FileModel:
    return _Builder(lex(text), proclib).build()

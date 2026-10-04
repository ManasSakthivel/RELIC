"""
Source-level mutation of JCL files.

Each operator rewrites JCL *text* to simulate a documented class of
modernization failure (docs/failure_taxonomy.md). The detectors then see only
the original and the mutated text; the ground-truth label comes from the
independent oracle (``jcl_oracle``), never from the operator's intent.

Sites are enumerated exhaustively and deterministically — there is no random
sampling and therefore no seed. Edits are minimal and made in place (column
positions and sequence numbers of untouched text are preserved) so that a
mutant differs from its original only by the intended change.

Operators (intent -> taxonomy):

  F1  SWAP_ADJACENT_STEPS            reorder two consecutive steps
  F1  SPLIT_JOB                      start a new, independently scheduled job
                                     before a step (dependency dropped)
  F2  DELETE_PRODUCER_STEP           remove a step whose output a later step uses
  F2  RENAME_OUTPUT_DATASET          rename the producer side of a dataset only
  F2  MOVE_CONSUMER_BEFORE_PRODUCER  schedule a consumer before its producer
  F3  REMOVE_COND                    drop an EXEC COND= return-code guard
  F3  ALTER_COND_THRESHOLD           change the code of the first COND test
  F3  REMOVE_IF_GUARD                drop an IF/THEN/ELSE/ENDIF construct
  --  INSERT_COMMENT                 add a comment statement between steps
  --  CHANGE_MSGCLASS                change the JOB card's output class

The last two are semantics-preserving refactorings by design (expected
negatives). Fault operators can also yield behaviourally equivalent mutants;
the oracle labels those as negatives.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from jcl_oracle.lexer import Statement, lex, parse_operands, split_top, unparen
from jcl_oracle.model import substitute

STMT_COLS = 71

FAULT_OPERATORS = [
    "SWAP_ADJACENT_STEPS",
    "SPLIT_JOB",
    "DELETE_PRODUCER_STEP",
    "RENAME_OUTPUT_DATASET",
    "MOVE_CONSUMER_BEFORE_PRODUCER",
    "REMOVE_COND",
    "ALTER_COND_THRESHOLD",
    "REMOVE_IF_GUARD",
]
NEGATIVE_OPERATORS = ["INSERT_COMMENT", "CHANGE_MSGCLASS"]
ALL_OPERATORS = FAULT_OPERATORS + NEGATIVE_OPERATORS

OPERATOR_CATEGORY = {
    "SWAP_ADJACENT_STEPS": "F1_ORDERING",
    "SPLIT_JOB": "F1_ORDERING",
    "DELETE_PRODUCER_STEP": "F2_DATASET",
    "RENAME_OUTPUT_DATASET": "F2_DATASET",
    "MOVE_CONSUMER_BEFORE_PRODUCER": "F2_DATASET",
    "REMOVE_COND": "F3_RETURN_CODE",
    "ALTER_COND_THRESHOLD": "F3_RETURN_CODE",
    "REMOVE_IF_GUARD": "F3_RETURN_CODE",
    "INSERT_COMMENT": "NEGATIVE_REFACTOR",
    "CHANGE_MSGCLASS": "NEGATIVE_REFACTOR",
}

# RELIC contract type each operator is designed to violate.
OPERATOR_CONTRACT_TYPE = {
    "SWAP_ADJACENT_STEPS": "TEMPORAL",
    "SPLIT_JOB": "TEMPORAL",
    "DELETE_PRODUCER_STEP": "RESOURCE",
    "RENAME_OUTPUT_DATASET": "RESOURCE",
    "MOVE_CONSUMER_BEFORE_PRODUCER": "RESOURCE",
    "REMOVE_COND": "CONTROL_FLOW",
    "ALTER_COND_THRESHOLD": "CONTROL_FLOW",
    "REMOVE_IF_GUARD": "CONTROL_FLOW",
    "INSERT_COMMENT": "NONE",
    "CHANGE_MSGCLASS": "NONE",
}

_BOUNDARY_OPS = {"EXEC", "IF", "ELSE", "ENDIF", "JOB", "PROC", "PEND", "SET",
                 "JCLLIB", "INCLUDE", "OUTPUT", "CNTL", "ENDCNTL", "EXPORT"}


@dataclass
class Block:
    """A top-level job step: its EXEC statement and the lines that follow."""
    index: int
    name: str
    job: int
    context: tuple            # IF-nesting path: ((if_line, branch), ...)
    first_line: int
    last_line: int
    exec_stmt: Statement
    stmts: list[Statement] = field(default_factory=list)
    outputs: set[str] = field(default_factory=set)
    inputs: set[str] = field(default_factory=set)
    output_dds: list[tuple[Statement, str]] = field(default_factory=list)


@dataclass
class JobInfo:
    index: int
    stmt: Statement
    header: list[Statement]   # SET / JCLLIB / JOBLIB statements before the first step
    blocks: list[Block] = field(default_factory=list)


@dataclass
class IfInfo:
    if_stmt: Statement
    else_stmt: Statement | None
    endif_stmt: Statement | None


@dataclass
class Mutant:
    operator: str
    site: str
    text: str | None                 # None if the edit could not be made
    invalid_reason: str = ""
    scope_note: str = ""             # non-empty -> out of RELIC's declared scope
    expected_violation: bool = True

    def diff(self, original: str, path: str) -> str:
        if self.text is None:
            return ""
        return "".join(difflib.unified_diff(
            original.splitlines(keepends=True), self.text.splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}", n=1))


# ---------------------------------------------------------------------------
# Structure analysis
# ---------------------------------------------------------------------------

def _dsn_of(st: Statement, symbols: dict[str, str]) -> tuple[str | None, str]:
    _pos, kw = parse_operands(substitute(st.operands, symbols))
    dsn = kw.get("DSN", kw.get("DSNAME"))
    if dsn is None:
        return None, ""
    disp = kw.get("DISP")
    status = "NEW"
    if disp is not None:
        parts = split_top(unparen(disp))
        status = (parts[0] or "NEW").upper()
    return dsn.strip("'").upper(), status


def _idcams_names(data: list[str]) -> tuple[set[str], set[str]]:
    """(defined names, deleted names) from in-stream IDCAMS control statements."""
    text = " ".join(line[:72] for line in data).upper()
    defined = {m.group(1) for m in re.finditer(r"\bNAME\s*\(\s*([^()\s]+)\s*\)", text)}
    deleted = {m.group(1) for m in re.finditer(r"\bDELETE\s+\(?\s*([A-Z0-9@#$.&<>_-]+)", text)}
    return defined, deleted


def analyse(text: str) -> tuple[list[JobInfo], list[IfInfo], list[str]]:
    stmts = lex(text)
    jobs: list[JobInfo] = []
    ifs: list[IfInfo] = []
    lines = text.splitlines()
    in_proc = False
    stack: list[IfInfo] = []
    ctx: list[tuple[int, str]] = []
    cur_block: Block | None = None
    symbols: dict[str, str] = {}
    seen_step = False

    def close_block(end: int) -> None:
        nonlocal cur_block
        if cur_block is not None:
            cur_block.last_line = end
            cur_block = None

    for st in stmts:
        if st.kind == "STMT" and st.op in _BOUNDARY_OPS | {"PEND"}:
            close_block(st.first_line - 1)
        if st.kind == "NULL":
            close_block(st.first_line - 1)
        if st.kind != "STMT":
            if cur_block is not None:
                cur_block.stmts.append(st)
            continue
        if st.op == "PROC":
            in_proc = True
            continue
        if st.op == "PEND":
            in_proc = False
            continue
        if in_proc:
            continue
        if st.op == "JOB":
            jobs.append(JobInfo(len(jobs), st, []))
            symbols = {}
            seen_step = False
            ctx = []
            stack = []
            continue
        if not jobs:
            continue
        job = jobs[-1]
        if st.op == "SET":
            _p, kw = parse_operands(substitute(st.operands, symbols))
            for k, v in kw.items():
                symbols[k.upper()] = v.strip("'")
            if not seen_step:
                job.header.append(st)
            continue
        if st.op == "JCLLIB" and not seen_step:
            job.header.append(st)
            continue
        if st.op == "DD" and cur_block is None and not seen_step and st.name == "JOBLIB":
            job.header.append(st)
            continue
        if st.op == "IF":
            info = IfInfo(st, None, None)
            ifs.append(info)
            stack.append(info)
            ctx.append((st.first_line, "THEN"))
            continue
        if st.op == "ELSE":
            if stack:
                stack[-1].else_stmt = st
                ctx[-1] = (ctx[-1][0], "ELSE")
            continue
        if st.op == "ENDIF":
            if stack:
                stack[-1].endif_stmt = st
                stack.pop()
                ctx.pop()
            continue
        if st.op == "EXEC":
            seen_step = True
            b = Block(len(job.blocks), st.name or f"#{len(job.blocks) + 1}", job.index,
                      tuple(ctx), st.first_line, st.end_line, st, [st])
            job.blocks.append(b)
            cur_block = b
            continue
        if st.op == "DD" and cur_block is not None:
            cur_block.stmts.append(st)
            cur_block.last_line = max(cur_block.last_line, st.end_line)
            dsn, status = _dsn_of(st, symbols)
            if dsn and not dsn.startswith("*."):
                if status in {"NEW", "MOD"}:
                    cur_block.outputs.add(dsn)
                    cur_block.output_dds.append((st, dsn))
                else:
                    cur_block.inputs.add(dsn)
            if st.data and st.name.upper() in {"SYSIN"} and \
                    "IDCAMS" in cur_block.exec_stmt.operands.upper():
                defined, deleted = _idcams_names(st.data)
                cur_block.outputs |= defined
                cur_block.inputs |= deleted - defined
            continue
    close_block(len(lines) - 1)
    # Trailing comment lines after the last block belong to it; blocks never
    # extend past a NULL statement or the end of file.
    return jobs, ifs, lines


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _join(lines: list[str], trailing_newline: bool) -> str:
    return "\n".join(lines) + ("\n" if trailing_newline else "")


def _set_head(line: str, new_head: str) -> str | None:
    """Replace columns 1-71 of *line*, keeping columns 72-80. None on overflow."""
    head = new_head.rstrip()
    if len(head) > STMT_COLS:
        return None
    tail = line[STMT_COLS:]
    if tail.strip():
        return head.ljust(STMT_COLS) + tail
    return head


_COND_RE = re.compile(r"COND(?:\.[A-Z@#$][A-Z0-9@#$]*)?=(\((?:[^()]|\([^()]*\))*\)|[A-Z]+)", re.I)


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

def generate(text: str) -> list[Mutant]:
    jobs, ifs, lines = analyse(text)
    nl = text.endswith("\n")
    out: list[Mutant] = []

    def remove_ranges(ranges: list[tuple[int, int]]) -> list[str]:
        drop = set()
        for a, b in ranges:
            drop.update(range(a, b + 1))
        return [l for i, l in enumerate(lines) if i not in drop]

    for job in jobs:
        blocks = job.blocks

        # F1: SWAP_ADJACENT_STEPS
        for a, b in zip(blocks, blocks[1:]):
            if a.context != b.context or b.first_line != a.last_line + 1:
                continue
            new = lines[:a.first_line] + lines[b.first_line:b.last_line + 1] + \
                lines[a.first_line:a.last_line + 1] + lines[b.last_line + 1:]
            out.append(Mutant("SWAP_ADJACENT_STEPS", f"{a.name}<->{b.name}", _join(new, nl)))

        # F1: SPLIT_JOB
        for b in blocks[1:]:
            site = f"new job before {b.name}"
            if b.context:
                out.append(Mutant("SPLIT_JOB", site, None,
                                  invalid_reason="split point inside IF/THEN/ELSE"))
                continue
            jl = lines[job.stmt.first_line:job.stmt.last_line + 1]
            m = re.match(r"^//(\S+)", jl[0])
            jobname = m.group(1) if m else "JOB"
            newname = (jobname[:7] + ("2" if not jobname.endswith("2") else "3"))
            first = "//" + newname + jl[0][2 + len(jobname):]
            if len(newname) > len(jobname):
                # keep operands aligned: absorb into following blanks if possible
                rest = jl[0][2 + len(jobname):]
                if rest.startswith("  "):
                    first = "//" + newname + rest[len(newname) - len(jobname):]
            header = [first] + jl[1:]
            for h in job.header:
                header += lines[h.first_line:h.end_line + 1]
            new = lines[:b.first_line] + header + lines[b.first_line:]
            out.append(Mutant("SPLIT_JOB", site, _join(new, nl)))

        # F2: DELETE_PRODUCER_STEP
        for i, p in enumerate(blocks):
            consumers = [c for c in blocks[i + 1:] if p.outputs & c.inputs]
            if not consumers or len(blocks) < 2:
                continue
            new = remove_ranges([(p.first_line, p.last_line)])
            out.append(Mutant("DELETE_PRODUCER_STEP",
                              f"delete {p.name} (consumed by {','.join(c.name for c in consumers)})",
                              _join(new, nl)))

        # F2: RENAME_OUTPUT_DATASET
        for i, p in enumerate(blocks):
            for st, dsn in p.output_dds:
                consumers = [c for c in blocks[i + 1:] if dsn in c.inputs]
                site = f"{p.name}.{st.name or 'DD'} {dsn}"
                new_dsn_text = None
                m = re.match(r"^(.*?)(\([^()]*\))?$", dsn)
                base, suffix = (m.group(1), m.group(2) or "") if m else (dsn, "")
                if base.startswith("&&"):
                    new_base = base + "MG"
                    if len(new_base) - 2 > 8:
                        new_dsn_text = None
                    else:
                        new_dsn_text = new_base + suffix
                else:
                    new_base = base + ".MIG"
                    new_dsn_text = new_base + suffix if len(new_base) <= 44 else None
                scope = "" if consumers else \
                    "no consumer of this dataset inside the analysed JCL file (cross-file effect only)"
                if new_dsn_text is None:
                    out.append(Mutant("RENAME_OUTPUT_DATASET", site, None,
                                      invalid_reason="renamed DSN exceeds JCL length limits",
                                      scope_note=scope))
                    continue
                new_lines = list(lines)
                done = False
                for li in range(st.first_line, st.last_line + 1):
                    head = lines[li][:STMT_COLS]
                    mm = re.search(r"(DSN(?:AME)?=)('?)([^,\s']+)", head, re.I)
                    if mm:
                        # replace the base part, keep member/generation suffix as written
                        raw = mm.group(3)
                        rm = re.match(r"^(.*?)(\([^()]*\))?$", raw)
                        raw_base, raw_suffix = rm.group(1), rm.group(2) or ""
                        repl = raw_base + (".MIG" if not raw_base.startswith("&&") else "MG") + raw_suffix
                        new_head = head[:mm.start(3)] + repl + head[mm.end(3):]
                        nh = _set_head(lines[li], new_head)
                        if nh is None:
                            break
                        new_lines[li] = nh
                        done = True
                        break
                if not done:
                    out.append(Mutant("RENAME_OUTPUT_DATASET", site, None,
                                      invalid_reason="DSN could not be edited in place (column 71 overflow or layout)",
                                      scope_note=scope))
                    continue
                out.append(Mutant("RENAME_OUTPUT_DATASET", site, _join(new_lines, nl), scope_note=scope))

        # F2: MOVE_CONSUMER_BEFORE_PRODUCER
        for i, p in enumerate(blocks):
            for j in range(i + 2, len(blocks)):
                c = blocks[j]
                if not (p.outputs & c.inputs):
                    continue
                span = blocks[i:j + 1]
                if any(x.context != p.context for x in span) or \
                        any(y.first_line != x.last_line + 1 for x, y in zip(span, span[1:])):
                    continue
                moved = lines[c.first_line:c.last_line + 1]
                rest = lines[:c.first_line] + lines[c.last_line + 1:]
                new = rest[:p.first_line] + moved + rest[p.first_line:]
                out.append(Mutant("MOVE_CONSUMER_BEFORE_PRODUCER", f"{c.name} before {p.name}",
                                  _join(new, nl)))

        # F3: REMOVE_COND / ALTER_COND_THRESHOLD
        for b in blocks:
            st = b.exec_stmt
            for li in range(st.first_line, st.last_line + 1):
                head = lines[li][:STMT_COLS]
                m = _COND_RE.search(head)
                if not m:
                    continue
                # REMOVE_COND
                start, end = m.start(), m.end()
                prev_line_fix = None
                if start > 0 and head[start - 1] == ",":
                    new_head = head[:start - 1] + head[end:]
                elif end < len(head) and head[end] == ",":
                    new_head = head[:start] + head[end + 1:]
                else:
                    new_head = head[:start] + head[end:]
                    if li > st.first_line and not new_head[2:].strip():
                        prev_line_fix = li - 1
                new_lines = list(lines)
                invalid = ""
                if prev_line_fix is not None:
                    del new_lines[li]
                    ph = new_lines[prev_line_fix][:STMT_COLS]
                    idx = ph.rstrip().rfind(",")
                    fixed = _set_head(new_lines[prev_line_fix], ph[:idx] + ph[idx + 1:]) if idx >= 0 else None
                    if fixed is None:
                        invalid = "could not remove continuation comma"
                    else:
                        new_lines[prev_line_fix] = fixed
                else:
                    nh = _set_head(lines[li], new_head)
                    if nh is None:
                        invalid = "edit overflows column 71"
                    else:
                        new_lines[li] = nh
                out.append(Mutant("REMOVE_COND", f"{b.name} {m.group(0)}",
                                  None if invalid else _join(new_lines, nl), invalid_reason=invalid))
                # ALTER_COND_THRESHOLD: first numeric code inside the COND value
                val = m.group(1)
                nm = re.search(r"\d+", val)
                if nm is None:
                    out.append(Mutant("ALTER_COND_THRESHOLD", f"{b.name} {m.group(0)}", None,
                                      invalid_reason="COND has no numeric test (EVEN/ONLY)"))
                    break
                code = int(nm.group(0))
                new_code = min(code * 2, 4095) if code > 0 else 4
                vstart = m.start(1) + nm.start()
                vend = m.start(1) + nm.end()
                new_head = head[:vstart] + str(new_code) + head[vend:]
                nh = _set_head(lines[li], new_head)
                new_lines = list(lines)
                if nh is None:
                    out.append(Mutant("ALTER_COND_THRESHOLD", f"{b.name} {m.group(0)}", None,
                                      invalid_reason="edit overflows column 71"))
                else:
                    new_lines[li] = nh
                    out.append(Mutant("ALTER_COND_THRESHOLD",
                                      f"{b.name} {m.group(0)} -> code {new_code}",
                                      _join(new_lines, nl)))
                break

        # Negative refactorings (one each per multi-step job)
        if len(blocks) >= 2:
            b = blocks[1]
            new = lines[:b.first_line] + ["//* MIGRATION REVIEW: STEP ORDER VERIFIED"] + lines[b.first_line:]
            out.append(Mutant("INSERT_COMMENT", f"before {b.name}", _join(new, nl),
                              expected_violation=False))
            done = False
            for li in range(job.stmt.first_line, job.stmt.last_line + 1):
                head = lines[li][:STMT_COLS]
                mm = re.search(r"MSGCLASS=([A-Z0-9])", head, re.I)
                if mm:
                    newc = "X" if mm.group(1).upper() != "X" else "Y"
                    nh = _set_head(lines[li], head[:mm.start(1)] + newc + head[mm.end(1):])
                    new_lines = list(lines)
                    new_lines[li] = nh if nh is not None else lines[li]
                    out.append(Mutant("CHANGE_MSGCLASS", f"MSGCLASS {mm.group(1)}->{newc}",
                                      _join(new_lines, nl), expected_violation=False))
                    done = True
                    break

    # F3: REMOVE_IF_GUARD (file level)
    for info in ifs:
        if info.endif_stmt is None:
            continue
        ranges = [(info.if_stmt.first_line, info.if_stmt.last_line),
                  (info.endif_stmt.first_line, info.endif_stmt.last_line)]
        if info.else_stmt is not None:
            ranges.append((info.else_stmt.first_line, info.else_stmt.last_line))
        new = remove_ranges(ranges)
        out.append(Mutant("REMOVE_IF_GUARD", f"IF at line {info.if_stmt.first_line + 1}",
                          _join(new, nl),
                          scope_note="IF/THEN/ELSE/ENDIF is outside RELIC's declared parser scope "
                                     "(jcl_parser.py: 'noted but not deeply parsed')"))

    for mu in out:
        if mu.text is not None and mu.text == text:
            mu.text = None
            mu.invalid_reason = mu.invalid_reason or "mutant identical to original"
    return out

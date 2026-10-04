"""
Scenario simulation of JCL jobs.

Semantics follow the IBM z/OS MVS JCL Reference:

* steps run in document order inside a job;
* EXEC COND: the step is bypassed if any test ``code op RC`` is true; a test
  naming a step that did not run is ignored; a test without a step name is
  applied to every previously executed step; after an abend only steps with
  COND=EVEN / COND=ONLY (or inside an IF that tests ABEND/RUN) run;
* JOB COND: once any test is true, the remaining steps are bypassed;
* IF/THEN/ELSE: ``RC`` is the highest return code of the steps executed so
  far; ``step.RC`` on a step that did not run makes the relation false;
* allocation: DISP=OLD/SHR of a non-existent dataset and DISP=NEW of an
  existing dataset are JCL errors that end the job (SMS-managed assumption);
* disposition: DISP=NEW defaults to DELETE, existing datasets to KEEP;
  the abnormal disposition applies when the step abends; temporary (&&)
  datasets are deleted at end of job;
* program effects come from ``jcl_oracle.programs``.

Return codes are partly *endogenous* (IDCAMS DELETE of a missing dataset
gives 8, DEFINE of an existing one gives 12, SET MAXCC/LASTCC) and partly
*injected* by the scenario (step X ends with RC v, or abends), which models
failures inside programs that the JCL cannot reveal.
"""

from __future__ import annotations

import hashlib
import itertools
import re
from dataclasses import dataclass, field

from jcl_oracle.model import DD, DSRef, FileModel, IfBlock, Item, Job, Step, iter_steps, split_top, unparen
from jcl_oracle.programs import ProgramEffect, dd_for, program_effect

_MEMBER_RE = re.compile(r"^(.*)\(([A-Z@#$][A-Z0-9@#$]{0,7})\)$")
_GDG_RE = re.compile(r"^(.*)\(([+-]?\d+)\)$")

ABEND = "ABEND"


def alloc_name(key: str) -> str:
    """Name used for catalog existence checks (PDS member -> library)."""
    m = _MEMBER_RE.match(key)
    if m and not _GDG_RE.match(key):
        return m.group(1)
    return key


def _h(*parts: object) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12]


@dataclass(frozen=True)
class Scenario:
    target: str | None = None          # step identity
    value: object = None               # int RC or "ABEND"

    def label(self) -> str:
        return "baseline" if self.target is None else f"{self.target}={self.value}"


@dataclass(frozen=True)
class Behavior:
    steps: frozenset            # (ident, status, rc)
    reads: frozenset            # (ident, key, version)
    final: frozenset            # (key, version) for permanent datasets/members
    termination: tuple          # per job: ("OK",) or ("JCLERR", ident, reason)


@dataclass
class StepRecord:
    ident: str
    name: str
    status: str                 # RUN, ABEND, BYPASS, NOTRUN, JCLERR
    rc: int | None = None


@dataclass
class _JobCtx:
    job: Job
    results: list[StepRecord] = field(default_factory=list)
    terminated: bool = False
    term_reason: tuple = ("OK",)
    abended: bool = False


# ---------------------------------------------------------------------------
# COND parsing / evaluation
# ---------------------------------------------------------------------------

def parse_cond(cond: str | None) -> tuple[list[tuple[int, str, str | None]], bool, bool]:
    """Return (tests, even, only)."""
    if not cond:
        return [], False, False
    c = cond.strip().upper()
    even = only = False
    tests: list[tuple[int, str, str | None]] = []
    inner = unparen(c)
    parts = split_top(inner)
    # Single test written without outer parentheses: (4,LT) or (4,LT,STEP1)
    if parts and parts[0].isdigit():
        groups = [inner]
    else:
        groups = parts
    for g in groups:
        g = g.strip()
        if g == "EVEN":
            even = True
            continue
        if g == "ONLY":
            only = True
            continue
        fields = [f.strip() for f in unparen(g).split(",")]
        if len(fields) >= 2 and fields[0].isdigit():
            ref = fields[2] if len(fields) > 2 and fields[2] else None
            tests.append((int(fields[0]), fields[1], ref))
    return tests, even, only


def _cmp(code: int, op: str, rc: int) -> bool:
    return {
        "GT": code > rc, "GE": code >= rc, "EQ": code == rc,
        "LT": code < rc, "LE": code <= rc, "NE": code != rc,
    }.get(op, False)


def cond_constants(model: FileModel) -> set[int]:
    vals: set[int] = set()
    for job in model.jobs:
        for c in [job.cond] + [s.cond for s in iter_steps(job.items)]:
            for code, _op, _ref in parse_cond(c)[0]:
                vals.add(code)
        for blk in _iter_ifs(job.items):
            for m in re.finditer(r"\b(\d+)\b", blk.expr):
                vals.add(int(m.group(1)))
    return vals


def _iter_ifs(items: list[Item]) -> list[IfBlock]:
    out: list[IfBlock] = []
    for it in items:
        if isinstance(it, IfBlock):
            out.append(it)
            out.extend(_iter_ifs(it.then_items))
            out.extend(_iter_ifs(it.else_items))
    return out


# ---------------------------------------------------------------------------
# IF expression evaluation
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"\s*(>=|<=|¬=|!=|¬>|¬<|>|<|=|¬|!|&|\||\(|\)|[A-Z0-9@#$.]+)", re.I)
_RELOPS = {
    "GT": "GT", ">": "GT", "GE": "GE", ">=": "GE", "NL": "GE", "¬<": "GE",
    "LT": "LT", "<": "LT", "LE": "LE", "<=": "LE", "NG": "LE", "¬>": "LE",
    "EQ": "EQ", "=": "EQ", "NE": "NE", "¬=": "NE", "!=": "NE",
}


class _IfEval:
    def __init__(self, expr: str, ctx: _JobCtx, prefix: str):
        self.toks = [t.upper() for t in _TOKEN_RE.findall(expr) if t.strip()]
        self.i = 0
        self.ctx = ctx
        self.prefix = prefix

    def peek(self) -> str | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self) -> str:
        t = self.toks[self.i]
        self.i += 1
        return t

    def parse(self) -> bool:
        if not self.toks:
            return False
        v = self.or_()
        return v

    def or_(self) -> bool:
        v = self.and_()
        while self.peek() in {"OR", "|"}:
            self.take()
            r = self.and_()
            v = v or r
        return v

    def and_(self) -> bool:
        v = self.not_()
        while self.peek() in {"AND", "&"}:
            self.take()
            r = self.not_()
            v = v and r
        return v

    def not_(self) -> bool:
        if self.peek() in {"NOT", "¬", "!"}:
            self.take()
            return not self.not_()
        return self.primary()

    def primary(self) -> bool:
        if self.peek() == "(":
            self.take()
            v = self.or_()
            if self.peek() == ")":
                self.take()
            return v
        operand = self.take() if self.peek() is not None else ""
        op = None
        val = None
        if self.peek() in _RELOPS:
            op = _RELOPS[self.take()]
            val = self.take() if self.peek() is not None else "0"
        return self.relation(operand, op, val)

    def _find(self, stepname: str) -> StepRecord | None:
        cands = [self.prefix + stepname, stepname]
        for name in cands:
            for rec in reversed(self.ctx.results):
                if rec.name == name:
                    return rec
        return None

    def relation(self, operand: str, op: str | None, val: str | None) -> bool:
        parts = operand.split(".")
        kw = parts[-1]
        stepname = ".".join(parts[:-1])
        if kw == "RC":
            if stepname:
                rec = self._find(stepname)
                if rec is None or rec.status != "RUN":
                    return False
                rc = rec.rc or 0
            else:
                rcs = [r.rc or 0 for r in self.ctx.results if r.status == "RUN"]
                rc = max(rcs) if rcs else 0
            try:
                n = int(val or "0")
            except ValueError:
                return False
            return _cmp(rc, op or "EQ", n)  # relation is "RC op n"
        if kw in {"ABEND", "RUN"}:
            if kw == "ABEND":
                truth = (self._find(stepname) is not None and self._find(stepname).status == "ABEND") \
                    if stepname else self.ctx.abended
            else:
                rec = self._find(stepname) if stepname else None
                truth = rec is not None and rec.status in {"RUN", "ABEND"}
            if op is None:
                return truth
            want = (val or "TRUE") == "TRUE"
            return (truth == want) if op == "EQ" else (truth != want)
        if kw == "ABENDCC":
            return False
        return False


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------

class Simulator:
    """Simulate a FileModel under scenarios. One instance per file version."""

    def __init__(self, model: FileModel, cobol_sources: dict[str, str] | None,
                 initial: dict[str, bool]):
        self.model = model
        self.cobol_sources = cobol_sources or {}
        self.initial = initial
        self._effects: dict[int, ProgramEffect] = {}

    def effect(self, step: Step) -> ProgramEffect:
        k = id(step)
        if k not in self._effects:
            self._effects[k] = program_effect(step, self.cobol_sources)
        return self._effects[k]

    # -- public -------------------------------------------------------------

    def behaviors(self, scenario: Scenario) -> frozenset:
        jobs = self.model.jobs
        if len(jobs) <= 1:
            orders = [tuple(range(len(jobs)))]
        elif len(jobs) <= 4:
            orders = list(itertools.permutations(range(len(jobs))))
        else:
            orders = [tuple(range(len(jobs)))]
        return frozenset(self.run(scenario, order)[0] for order in orders)

    def run(self, scenario: Scenario, order: tuple[int, ...] | None = None):
        if order is None:
            order = tuple(range(len(self.model.jobs)))
        versions: dict[str, str] = {k: f"INIT:{k}" for k, v in self.initial.items() if v}
        writers: dict[str, str] = {}
        state = {"versions": versions, "writers": writers, "steps": [], "reads": [],
                 "dataflow": []}
        terms: list[tuple] = []
        records: dict[int, list[StepRecord]] = {}
        for ji in order:
            job = self.model.jobs[ji]
            ctx = _JobCtx(job)
            self._run_items(job.items, ctx, state, scenario, selected=True, abend_ok=False)
            for k in [k for k in versions if k.startswith("&&")]:
                del versions[k]
            terms.append((job.name,) + ctx.term_reason)
            records[ji] = ctx.results
        beh = Behavior(
            steps=frozenset((r.ident, r.status, r.rc) for r in state["steps"]),
            reads=frozenset(state["reads"]),
            final=frozenset((k, v) for k, v in versions.items() if not k.startswith("&&")),
            termination=tuple(sorted(terms)),
        )
        return beh, state

    # -- items --------------------------------------------------------------

    def _run_items(self, items: list[Item], ctx: _JobCtx, state: dict, scen: Scenario,
                   selected: bool, abend_ok: bool) -> None:
        for it in items:
            if isinstance(it, Step):
                self._run_step(it, ctx, state, scen, selected, abend_ok)
            else:
                if selected and not ctx.terminated:
                    prefix = ""
                    val = _IfEval(it.expr, ctx, prefix).parse()
                    tests_abend = bool(re.search(r"ABEND|\bRUN\b", it.expr, re.I))
                    self._run_items(it.then_items, ctx, state, scen, val, abend_ok or tests_abend)
                    self._run_items(it.else_items, ctx, state, scen, not val, abend_ok or tests_abend)
                else:
                    self._run_items(it.then_items, ctx, state, scen, False, abend_ok)
                    self._run_items(it.else_items, ctx, state, scen, False, abend_ok)

    def _record(self, ctx: _JobCtx, state: dict, rec: StepRecord) -> None:
        ctx.results.append(rec)
        state["steps"].append(rec)

    def _find_by_name(self, ctx: _JobCtx, name: str, prefix: str) -> StepRecord | None:
        for cand in ([prefix + name] if prefix else []) + [name]:
            for rec in reversed(ctx.results):
                if rec.name == cand:
                    return rec
        return None

    def _bypass_by_cond(self, step: Step, ctx: _JobCtx) -> bool:
        tests, even, only = parse_cond(step.cond)
        if ctx.abended and not (even or only):
            return True
        if only and not ctx.abended:
            return True
        for code, op, ref in tests:
            if ref:
                rec = self._find_by_name(ctx, ref, step.proc_prefix)
                if rec is None or rec.status != "RUN":
                    continue
                if _cmp(code, op, rec.rc or 0):
                    return True
            else:
                for rec in ctx.results:
                    if rec.status == "RUN" and _cmp(code, op, rec.rc or 0):
                        return True
        return False

    def _job_cond_stop(self, ctx: _JobCtx) -> bool:
        tests, _e, _o = parse_cond(ctx.job.cond)
        for code, op, _ref in tests:
            for rec in ctx.results:
                if rec.status == "RUN" and _cmp(code, op, rec.rc or 0):
                    return True
        return False

    # -- one step -----------------------------------------------------------

    def _run_step(self, step: Step, ctx: _JobCtx, state: dict, scen: Scenario,
                  selected: bool, abend_ok: bool) -> None:
        if ctx.terminated:
            self._record(ctx, state, StepRecord(step.ident, step.name, "NOTRUN"))
            return
        if not selected:
            self._record(ctx, state, StepRecord(step.ident, step.name, "BYPASS"))
            return
        if self._job_cond_stop(ctx):
            self._record(ctx, state, StepRecord(step.ident, step.name, "BYPASS"))
            return
        tests, even, only = parse_cond(step.cond)
        if ctx.abended and abend_ok and not (even or only):
            bypass = False
            # IF tested ABEND/RUN: honour remaining COND tests only
            for code, op, ref in tests:
                rec = self._find_by_name(ctx, ref, step.proc_prefix) if ref else None
                if ref and rec is not None and rec.status == "RUN" and _cmp(code, op, rec.rc or 0):
                    bypass = True
        else:
            bypass = self._bypass_by_cond(step, ctx)
        if bypass:
            self._record(ctx, state, StepRecord(step.ident, step.name, "BYPASS"))
            return

        versions: dict[str, str] = state["versions"]
        writers: dict[str, str] = state["writers"]

        # --- allocation ---------------------------------------------------
        for ddname, dd in step.dds.items():
            for ref in dd.refs:
                an = alloc_name(ref.key)
                exists = an in versions
                if ref.status == "NEW":
                    if exists and not ref.key.startswith("&&"):
                        self._jcl_error(ctx, state, step, f"NEW dataset already exists: {an}")
                        return
                    if ref.key not in versions:
                        versions[ref.key] = f"EMPTY:{_h(step.ident, ref.key)}"
                        writers[versions[ref.key]] = step.ident
                elif ref.status == "MOD":
                    if not exists:
                        versions[an] = f"EMPTY:{_h(step.ident, an)}"
                        writers[versions[an]] = step.ident
                else:  # OLD / SHR
                    if not exists:
                        self._jcl_error(ctx, state, step, f"dataset not found: {an}")
                        return

        # --- program execution -------------------------------------------------
        eff = self.effect(step)
        reads: list[tuple[str, str]] = []
        instream = tuple(sorted((n, _h(*d.instream)) for n, d in step.dds.items() if d.instream))
        base_sig = (step.ident, step.pgm, step.proc_unexpanded, step.parm, instream)

        def read_key(key: str) -> None:
            v = versions.get(key)
            if v is None:
                v = versions.get(alloc_name(key)) if alloc_name(key) != key else None
            if v is None:
                v = "ABSENT"
            reads.append((key, v))
            state["reads"].append((step.ident, key, v))
            w = writers.get(v)
            if w is not None and w != step.ident:
                state["dataflow"].append((w, step.ident, key))

        def write_key(key: str, tag: str) -> None:
            v = f"W:{_h(base_sig, tuple(reads), tag, key)}"
            versions[key] = v
            writers[v] = step.ident

        # program library (STEPLIB / JOBLIB member = program)
        if step.pgm and eff.reads_program_library:
            libs = [r.key for r in (step.dds["STEPLIB"].refs if "STEPLIB" in step.dds else ctx.job.joblib)]
            for lib in libs:
                read_key(f"{alloc_name(lib)}({step.pgm})")

        endogenous = 0
        if eff.catalog_ops:
            maxcc = 0
            lastcc = 0
            for i, op in enumerate(eff.catalog_ops):
                cc = 0
                if op.verb == "FILE_R":
                    dd = dd_for(step, op.name)
                    if dd is None or not dd.refs:
                        cc = 12 if dd is None else 0
                    else:
                        for r in dd.refs:
                            read_key(r.key)
                elif op.verb == "FILE_W":
                    dd = dd_for(step, op.name)
                    if dd is None or not dd.refs:
                        cc = 12 if dd is None else 0
                    else:
                        write_key(dd.refs[0].key, f"op{i}")
                elif op.verb == "DELETE":
                    if op.name in versions or alloc_name(op.name) in versions:
                        for k in [k for k in versions if k == op.name or k.startswith(op.name + "(")]:
                            del versions[k]
                    else:
                        cc = 8
                elif op.verb == "DEFINE":
                    if op.name in versions or (op.other and op.other not in versions):
                        cc = 12
                    else:
                        if op.other:
                            read_key(op.other)
                        write_key(op.name, f"define{i}")
                elif op.verb == "READ":
                    if op.name in versions:
                        read_key(op.name)
                    else:
                        cc = 12
                elif op.verb == "WRITE":
                    if op.name in versions:
                        write_key(op.name, f"op{i}")
                    else:
                        cc = 12
                elif op.verb == "RENAME":
                    if op.name in versions and op.other not in versions:
                        versions[op.other] = versions.pop(op.name)
                    else:
                        cc = 12
                elif op.verb in {"SETCC", "IFSET"}:
                    if op.verb == "IFSET":
                        var, rel, num = op.name.split("|")
                        current = lastcc if var == "LASTCC" else maxcc
                        if not _cmp(current, rel, int(num)):
                            continue
                    # IBM: SET MAXCC sets MAXCC; SET LASTCC sets LASTCC and raises
                    # MAXCC if the new value is higher.
                    if op.kind == "MAXCC":
                        maxcc = op.value
                    else:
                        lastcc = op.value
                        maxcc = max(maxcc, op.value)
                    continue
                lastcc = cc
                maxcc = max(maxcc, cc)
            endogenous = maxcc
        for acc in eff.accesses:
            if acc.mode in {"R", "RW"}:
                dd = dd_for(step, acc.ddname)
                if dd is not None:
                    for r in dd.refs:
                        read_key(r.key)
        for acc in eff.accesses:
            if acc.mode in {"W", "RW"}:
                dd = dd_for(step, acc.ddname)
                if dd is not None and dd.refs:
                    write_key(dd.refs[0].key, f"acc:{acc.ddname}")

        # --- completion --------------------------------------------------------
        abended = False
        rc = endogenous
        if scen.target == step.ident:
            if scen.value == ABEND:
                abended = True
            else:
                rc = max(rc, int(scen.value))  # type: ignore[arg-type]
        status = "ABEND" if abended else "RUN"
        self._record(ctx, state, StepRecord(step.ident, step.name, status, None if abended else rc))
        if abended:
            ctx.abended = True

        # --- dispositions -------------------------------------------------------
        for dd in step.dds.values():
            for ref in dd.refs:
                normal = ref.normal or ("DELETE" if ref.status == "NEW" else "KEEP")
                disp = (ref.abnormal or normal) if abended else normal
                if disp in {"DELETE", "UNCATLG"}:
                    # DELETE applies to the whole dataset (a PDS with all members).
                    an = alloc_name(ref.key)
                    for k in [k for k in versions if k == an or k.startswith(an + "(")]:
                        del versions[k]

    def _jcl_error(self, ctx: _JobCtx, state: dict, step: Step, reason: str) -> None:
        self._record(ctx, state, StepRecord(step.ident, step.name, "JCLERR"))
        ctx.terminated = True
        ctx.term_reason = ("JCLERR", step.ident, reason)


# ---------------------------------------------------------------------------
# Initial catalog state
# ---------------------------------------------------------------------------

def first_access_creates(model: FileModel, cobol_sources: dict[str, str] | None) -> dict[str, bool]:
    """For every dataset key, does its first access in document order create it?

    Returns key -> initially_exists. A key whose first access is DISP=NEW or an
    IDCAMS DEFINE does not exist before the job; any other first access
    (OLD/SHR/MOD, DELETE, REPRO, ...) implies it exists. Temporary (&&)
    datasets never exist initially."""
    seen: dict[str, bool] = {}

    def note(key: str, creates: bool) -> None:
        if key.startswith("&&"):
            seen.setdefault(key, False)
            return
        if key not in seen:
            seen[key] = not creates
        an = alloc_name(key)
        if an != key and an not in seen:
            seen[an] = True  # writing a member requires the library to exist

    for step in model.steps():
        eff = program_effect(step, cobol_sources)
        for dd in step.dds.values():
            for ref in dd.refs:
                note(ref.key, ref.status == "NEW")
        for op in eff.catalog_ops:
            if op.verb == "DEFINE":
                if op.other:
                    note(op.other, False)
                note(op.name, True)
            elif op.verb in {"DELETE", "READ", "WRITE", "RENAME"} and op.name:
                note(op.name, False)
        if step.pgm:
            for lib in ([r.key for r in step.dds["STEPLIB"].refs] if "STEPLIB" in step.dds else []):
                note(f"{alloc_name(lib)}({step.pgm})", False)
    return seen

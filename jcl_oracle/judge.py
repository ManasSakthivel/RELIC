"""
Behavioural comparison of two versions of a JCL file.

``compare_versions(original, mutated)`` simulates both versions under the
same scenario set and the same initial catalog, and returns a Verdict:

* DIFFERENT — at least one scenario produces a different observable
  (executed steps / return codes, data read by a step, final catalog
  content, or job termination);
* EQUIVALENT — no scenario differs and every opaque step is unaffected;
* UNDETERMINED — no modelled observable differs, but an opaque step (whose
  side effects the oracle cannot model) changed position, presence, job,
  or DD set, so equivalence cannot be asserted.

Also provides ``describe_file`` (semantic facts used for contract-recovery
evaluation).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from jcl_oracle.model import FileModel, ProcLibrary, Step, build_model, iter_steps
from jcl_oracle.simulate import (
    ABEND,
    Behavior,
    Scenario,
    Simulator,
    cond_constants,
    first_access_creates,
    parse_cond,
)

BASE_RC_VALUES = (4, 8, 12, 16)
MAX_RC = 4095


@dataclass
class Verdict:
    label: str                                   # DIFFERENT / EQUIVALENT / UNDETERMINED / INVALID
    categories: list[str] = field(default_factory=list)   # observable categories that differ
    evidence: list[str] = field(default_factory=list)     # human-readable witnesses
    scenarios_checked: int = 0
    differing_scenarios: int = 0
    opaque_touched: list[str] = field(default_factory=list)
    model_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "categories": self.categories,
            "evidence": self.evidence[:5],
            "scenarios_checked": self.scenarios_checked,
            "differing_scenarios": self.differing_scenarios,
            "opaque_touched": self.opaque_touched,
            "model_errors": self.model_errors,
        }


SCENARIO_SETS = ("full", "no_abend")


def _scenarios(m1: FileModel, m2: FileModel, scenario_set: str = "full") -> list[Scenario]:
    idents: list[str] = []
    for m in (m1, m2):
        for s in m.steps():
            if s.ident not in idents:
                idents.append(s.ident)
    values: set[int] = set(BASE_RC_VALUES)
    for c in cond_constants(m1) | cond_constants(m2):
        for v in (c - 1, c, c + 1):
            if 0 < v <= MAX_RC:
                values.add(v)
    scen = [Scenario()]
    for ident in idents:
        for v in sorted(values):
            scen.append(Scenario(ident, v))
        if scenario_set == "full":
            scen.append(Scenario(ident, ABEND))
    return scen


def _canonical(x) -> str:
    """repr() with every set sorted: independent of the per-process hash seed."""
    if isinstance(x, (set, frozenset)):
        return "{" + ", ".join(sorted(_canonical(v) for v in x)) + "}"
    if isinstance(x, (tuple, list)):
        return "(" + ", ".join(_canonical(v) for v in x) + ")"
    if hasattr(x, "__dataclass_fields__"):
        return type(x).__name__ + _canonical(tuple(getattr(x, f) for f in x.__dataclass_fields__))
    return repr(x)


def _diff_categories(a: frozenset, b: frozenset) -> tuple[list[str], str]:
    """Categories that differ between two sets of behaviours (one per job order)."""
    cats: set[str] = set()
    witness = ""
    la, lb = sorted(a, key=_canonical), sorted(b, key=_canonical)
    for x, y in zip(la, lb):
        if x.steps != y.steps:
            cats.add("execution")
            d = sorted(x.steps ^ y.steps)
            witness = witness or f"execution: {d[:4]}"
        if x.reads != y.reads:
            cats.add("dataflow")
            d = sorted(x.reads ^ y.reads)
            witness = witness or f"dataflow: {d[:3]}"
        if x.final != y.final:
            cats.add("final_catalog")
            d = sorted(x.final ^ y.final)
            witness = witness or f"final_catalog: {d[:3]}"
        if x.termination != y.termination:
            cats.add("termination")
            witness = witness or f"termination: {x.termination} vs {y.termination}"
    if len(la) != len(lb):
        cats.add("job_orders")
    return sorted(cats), witness


def _opaque_context(model: FileModel, sim: Simulator) -> dict[str, tuple]:
    """For each opaque step: (job index, predecessor identities, DD signature, pgm)."""
    ctx: dict[str, tuple] = {}
    for ji, job in enumerate(model.jobs):
        before: list[str] = []
        for st in iter_steps(job.items):
            eff = sim.effect(st)
            if eff.opaque_reasons:
                dd_sig = tuple(sorted(
                    (n, tuple((r.key, r.status) for r in d.refs), tuple(d.instream))
                    for n, d in st.dds.items()))
                ctx[st.ident] = (ji, frozenset(before), dd_sig, st.pgm, st.proc_unexpanded)
            before.append(st.ident)
    return ctx


def compare_versions(original: str, mutated: str, proclib: ProcLibrary | None = None,
                     cobol_sources: dict[str, str] | None = None,
                     scenario_set: str = "full") -> Verdict:
    """
    scenario_set:
      "full"     — baseline, every step ending with each RC value, and every
                   step abending (primary ground truth);
      "no_abend" — the same without abend scenarios (sensitivity analysis:
                   behaviour under normal completion only).
    """
    if scenario_set not in SCENARIO_SETS:
        raise ValueError(f"unknown scenario_set {scenario_set!r}")
    m1 = build_model(original, proclib)
    m2 = build_model(mutated, proclib)
    if m2.errors and not m1.errors:
        return Verdict("INVALID", model_errors=m2.errors)

    init = first_access_creates(m1, cobol_sources)
    for k, v in first_access_creates(m2, cobol_sources).items():
        init.setdefault(k, v)
    s1 = Simulator(m1, cobol_sources, init)
    s2 = Simulator(m2, cobol_sources, init)

    scenarios = _scenarios(m1, m2, scenario_set)
    cats: set[str] = set()
    evidence: list[str] = []
    ndiff = 0
    for sc in scenarios:
        b1 = s1.behaviors(sc)
        b2 = s2.behaviors(sc)
        if b1 != b2:
            ndiff += 1
            c, w = _diff_categories(b1, b2)
            cats.update(c)
            if len(evidence) < 5:
                evidence.append(f"[{sc.label()}] {w}")

    o1, o2 = _opaque_context(m1, s1), _opaque_context(m2, s2)
    touched = sorted(k for k in set(o1) | set(o2) if o1.get(k) != o2.get(k))

    if ndiff:
        label = "DIFFERENT"
    elif touched:
        label = "UNDETERMINED"
    else:
        label = "EQUIVALENT"
    return Verdict(label=label, categories=sorted(cats), evidence=evidence,
                   scenarios_checked=len(scenarios), differing_scenarios=ndiff,
                   opaque_touched=touched, model_errors=m2.errors)


# ---------------------------------------------------------------------------
# Semantic facts for contract-recovery evaluation (RQ1)
# ---------------------------------------------------------------------------

@dataclass
class FileFacts:
    steps: list[str]                         # top-level step names in document order
    order_pairs: set[tuple[str, str]]        # consecutive top-level steps within a job
    dataflow_pairs: set[tuple[str, str]]     # (producer, consumer) top-level steps
    cond_pairs: set[tuple[str, str]]         # (referenced, guarded) from EXEC COND
    if_pairs: set[tuple[str, str]]           # (referenced, guarded) from IF/THEN/ELSE
    opaque_steps: set[str]


def describe_file(text: str, proclib: ProcLibrary | None = None,
                  cobol_sources: dict[str, str] | None = None) -> FileFacts:
    model = build_model(text, proclib)
    init = first_access_creates(model, cobol_sources)
    sim = Simulator(model, cobol_sources, init)
    _beh, state = sim.run(Scenario())

    top = {}
    for st in model.steps():
        top[st.ident] = st.top_name or st.name or st.ident

    steps: list[str] = []
    order: set[tuple[str, str]] = set()
    cond_pairs: set[tuple[str, str]] = set()
    if_pairs: set[tuple[str, str]] = set()
    opaque: set[str] = set()
    for job in model.jobs:
        prev_top: str | None = None
        seen_tops: list[str] = []
        for st in iter_steps(job.items):
            t = top[st.ident]
            if sim.effect(st).opaque_reasons:
                opaque.add(t)
            if t != prev_top:
                if prev_top is not None:
                    order.add((prev_top, t))
                steps.append(t)
                prev_top = t
            tests, _e, _o = parse_cond(st.cond)
            for _code, _op, ref in tests:
                if ref:
                    ref_top = ref.split(".")[0] if ref.split(".")[0] in seen_tops else (
                        st.top_name if st.proc_prefix else ref.split(".")[0])
                    if ref_top != t:
                        cond_pairs.add((ref_top, t))
                else:
                    for p in seen_tops:
                        if p != t:
                            cond_pairs.add((p, t))
            if t not in seen_tops:
                seen_tops.append(t)
        _collect_if_pairs(job.items, [], top, if_pairs)

    dataflow = {(top[w], top[r]) for (w, r, _k) in state["dataflow"] if top.get(w) != top.get(r)}
    return FileFacts(steps, order, dataflow, cond_pairs, if_pairs, opaque)


def _collect_if_pairs(items, preceding: list[str], top: dict[str, str],
                      out: set[tuple[str, str]]) -> list[str]:
    import re
    from jcl_oracle.model import IfBlock
    for it in items:
        if isinstance(it, Step):
            t = top[it.ident]
            if t not in preceding:
                preceding = preceding + [t]
            continue
        refs: list[str] = []
        for m in re.finditer(r"([A-Z@#$][A-Z0-9@#$]*)(?:\.[A-Z@#$][A-Z0-9@#$]*)?\.(RC|ABEND|RUN|ABENDCC)\b",
                             it.expr.upper()):
            refs.append(m.group(1))
        bare = bool(re.search(r"(?<![.\w])(RC|ABEND|ABENDCC)\b", it.expr.upper()))
        sources = set(refs) | (set(preceding) if bare else set())
        guarded = [top[s.ident] for s in iter_steps(it.then_items + it.else_items)]
        for g in guarded:
            for s in sources:
                if s != g:
                    out.add((s, g))
        snapshot = list(preceding)
        after_then = _collect_if_pairs(it.then_items, snapshot, top, out)
        after_else = _collect_if_pairs(it.else_items, snapshot, top, out)
        for t in after_then + after_else:
            if t not in preceding:
                preceding = preceding + [t]
    return preceding

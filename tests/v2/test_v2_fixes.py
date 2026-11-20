"""
Regression tests for the RELIC V2 corrections (reports/v2/DEFECT_REGISTER.md).

* D-001  same-named steps collapsed into one IR entity
* D-002  DD parsing: ``DSNAME=`` alias and omitted DISP status ``DISP=(,PASS)``
* D-003  RESOURCE contracts ignored step order (consumer declared before producer)
* D-004  ``DISP=(MOD,DELETE)`` pre-delete idiom treated as a producer

Every fix is opt-in (``v2_fixes=True``); each test also asserts the default /
legacy behaviour so that the "before" state stays documented and the published
v1.0.0 / v1.1 results remain reproducible.

Syntax scope of the fixes (also stated in the register):
  * duplicate step names are disambiguated per FILE by occurrence number;
  * content-identical, identically named steps that are merely swapped remain
    undetectable by name-based identity (test_documented_limitation_*).
"""

from pathlib import Path

import pytest

from legacy_contract.bcg.builder import BCGBuilder
from legacy_contract.ir.model import EntityType, RelationType
from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.risk.detector import RiskDetector
from legacy_contract.static_analysis.extractor import StaticContractExtractor
from relic_eval.detectors import RelicDetector, neutral_record

ROOT = Path(__file__).resolve().parents[2]

DUP = """//J JOB A
//CREATE EXEC PGM=X
//CRTABS EXEC PGM=X,COND=(4,LT)
//CRTABS EXEC PGM=X,COND=(4,LT)
//CRTABS EXEC PGM=X,COND=(4,LT)
//LAST EXEC PGM=X
"""


def _ir(text, **kw):
    kw = {k: v for k, v in kw.items() if k != "v2_resource_order"}
    _r, ir = JCLParser(**kw).parse_lines(text.splitlines(), "t.jcl")
    return ir


def _steps(ir):
    return [e for e in ir.entities.values() if e.entity_type == EntityType.STEP]


def _bcg(text, **kw):
    ir = _ir(text, **kw)
    ext = StaticContractExtractor(
        legacy_v1_0=kw.get("legacy_v1_0", False), v2_fixes=kw.get("v2_fixes", False)
    ).extract(ir)
    return BCGBuilder().build(ir, ext)


def _flagged(orig, mut, **kw):
    rep = RiskDetector(legacy_v1_0=kw.get("legacy_v1_0", False)).detect(
        _bcg(orig, **kw), _bcg(mut, **kw), neutral_record()
    )
    return len(rep.risk_items) + len(rep.false_positive_candidates) > 0


# --------------------------------------------------------------------------
# D-001 step identity
# --------------------------------------------------------------------------

def test_d001_default_collapses_duplicate_step_names():
    """Before: 5 EXEC statements -> 3 STEP entities (the defect)."""
    assert len(_steps(_ir(DUP))) == 3


def test_d001_v2_keeps_every_step():
    ir = _ir(DUP, v2_fixes=True)
    names = [s.name for s in sorted(_steps(ir), key=lambda s: s.attributes["order"])]
    assert names == ["CREATE", "CRTABS", "CRTABS#2", "CRTABS#3", "LAST"]


def test_d001_v2_step_chain_is_complete_and_acyclic():
    ir = _ir(DUP, v2_fixes=True)
    precede = ir.get_relations_of_type(RelationType.MUST_PRECEDE)
    assert len(precede) == 4
    assert all(r.source.entity_id != r.target.entity_id for r in precede)


def test_d001_unnamed_steps_do_not_collide_across_jobs():
    text = "//J1 JOB A\n// EXEC PGM=X\n//J2 JOB A\n// EXEC PGM=X\n"
    assert len(_steps(_ir(text))) == 1                       # before: both are STEP_001
    assert len(_steps(_ir(text, v2_fixes=True))) == 2        # after


def test_d001_same_name_in_two_jobs_is_two_steps():
    text = "//J1 JOB A\n//S1 EXEC PGM=X\n//J2 JOB A\n//S1 EXEC PGM=X\n"
    assert len(_steps(_ir(text, v2_fixes=True))) == 2


def test_d001_removing_cond_on_a_duplicate_named_step_is_detected():
    """The motivating case: GenApp db2cre.jcl (REMOVE_COND on a later 'CRTABS')."""
    lines = DUP.splitlines(keepends=True)
    assert lines[3] == "//CRTABS EXEC PGM=X,COND=(4,LT)\n"      # 2nd CRTABS
    mut = "".join(lines[:3] + ["//CRTABS EXEC PGM=X\n"] + lines[4:])
    assert _flagged(DUP, mut) is False                       # before (v1.1): missed
    assert _flagged(DUP, mut, v2_fixes=True) is True         # after


def test_d001_deleting_a_duplicate_named_step_is_detected():
    lines = DUP.splitlines(keepends=True)
    mut = "".join(lines[:3] + lines[4:])                     # drop second CRTABS
    assert _flagged(DUP, mut, v2_fixes=True) is True


def test_d001_cond_stepname_resolves_to_nearest_preceding_duplicate():
    text = (
        "//J JOB A\n//A EXEC PGM=X\n//A EXEC PGM=X\n//B EXEC PGM=X,COND=(4,LT,A)\n"
    )
    ext = StaticContractExtractor(v2_fixes=True).extract(_ir(text, v2_fixes=True))
    refs = [c.metadata["ref_step"] for c in ext.control_flow_contracts]
    assert refs == ["A#2"]                                   # nearest preceding, not both
    legacy = StaticContractExtractor().extract(_ir(text))
    assert len(legacy.control_flow_contracts) == 1           # collapsed: one 'A'


def test_d001_no_change_when_step_names_are_unique():
    text = "//J JOB A\n//S1 EXEC PGM=X\n//S2 EXEC PGM=X,COND=(4,LT,S1)\n//S3 EXEC PGM=X\n"

    def sig(**kw):
        ir = _ir(text, **kw)
        ext = StaticContractExtractor(v2_fixes=kw.get("v2_fixes", False)).extract(ir)
        return sorted(
            (c.contract_type.value, ir.entities[c.subject_id].name, ir.entities[c.object_id].name)
            for c in ext.all_contracts
        )

    assert sig() == sig(v2_fixes=True)


def test_documented_limitation_swapped_identically_named_steps_not_detected():
    """
    Name-based identity cannot see that two steps with the same name (and the
    same contracts) were exchanged. Characterisation test: if this ever starts
    returning True, update reports/v2/DEFECT_REGISTER.md (D-001 limitation).
    """
    orig = ("//J JOB A\n//S EXEC PGM=X\n//D1 DD DSN=A.B,DISP=SHR\n"
            "//S EXEC PGM=Y\n//D1 DD DSN=C.D,DISP=SHR\n")
    mut = ("//J JOB A\n//S EXEC PGM=Y\n//D1 DD DSN=C.D,DISP=SHR\n"
           "//S EXEC PGM=X\n//D1 DD DSN=A.B,DISP=SHR\n")
    assert _flagged(orig, mut, v2_fixes=True) is False


# --------------------------------------------------------------------------
# D-002 DD parsing
# --------------------------------------------------------------------------

def _roles(text, **kw):
    ir = _ir(text, **kw)
    out = {}
    for r in ir.relations:
        if r.relation_type in (RelationType.PRODUCES, RelationType.CONSUMES):
            out[(r.source.name, r.target.name)] = r.relation_type.value
    return out


@pytest.mark.parametrize("dd,expected", [
    ("DSN=W.A,DISP=(,PASS)", "PRODUCES"),
    ("DSN=W.A,DISP=(,CATLG,DELETE)", "PRODUCES"),
    ("DSN=W.A,DISP=(NEW,CATLG)", "PRODUCES"),
    ("DSN=W.A,DISP=(MOD,PASS)", "PRODUCES"),
    ("DSN=W.A,DISP=SHR", "CONSUMES"),
    ("DSN=W.A,DISP=OLD", "CONSUMES"),
    ("DSN=W.A,DISP=(OLD,DELETE)", "CONSUMES"),
    ("DSN=W.A,DISP=(SHR,KEEP)", "CONSUMES"),
    ("DISP=(,PASS),DSN=W.A", "PRODUCES"),
])
def test_d002_disp_status_roles_v2(dd, expected):
    text = f"//J JOB A\n//S1 EXEC PGM=X\n//D DD {dd}\n"
    assert _roles(text, v2_fixes=True) == {("S1", "W.A"): expected}


def test_d002_omitted_disp_status_default_misreads_as_consumer():
    """Before: DISP=(,PASS) was captured as '(' and treated as a consumer."""
    text = "//J JOB A\n//S1 EXEC PGM=X\n//D DD DSN=W.A,DISP=(,PASS)\n"
    assert _roles(text) == {("S1", "W.A"): "CONSUMES"}
    assert _roles(text, v2_fixes=True) == {("S1", "W.A"): "PRODUCES"}


def test_d002_dsname_alias_is_recognised():
    text = "//J JOB A\n//S1 EXEC PGM=X\n//D DD DSNAME=W.A,DISP=SHR\n"
    assert _roles(text) == {}                                  # before: invisible
    assert _roles(text, v2_fixes=True) == {("S1", "W.A"): "CONSUMES"}


def test_d002_dsn_pattern_does_not_match_inside_other_keywords():
    text = "//J JOB A\n//S1 EXEC PGM=X\n//D DD XDSN=W.A,DISP=SHR\n"
    assert _roles(text, v2_fixes=True) == {}


def test_d002_resource_contract_recovered_for_omitted_status():
    text = ("//J JOB A\n//MAKE EXEC PGM=X\n//O DD DSN=W.A,DISP=(,PASS)\n"
            "//USE EXEC PGM=X\n//I DD DSN=W.A,DISP=(OLD,DELETE)\n")
    before = StaticContractExtractor().extract(_ir(text)).resource_contracts
    after = StaticContractExtractor(v2_fixes=True).extract(_ir(text, v2_fixes=True)).resource_contracts
    assert (len(before), len(after)) == (0, 1)


def test_d002_disp_absent_default_is_unchanged():
    """Scope limit: DD with DSN and no DISP stays 'consumer' (not changed in V2)."""
    text = "//J JOB A\n//S1 EXEC PGM=X\n//D DD DSN=W.A(M)\n"
    assert _roles(text) == _roles(text, v2_fixes=True) == {("S1", "W.A(M)"): "CONSUMES"}


# --------------------------------------------------------------------------
# Flags / detector wiring
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# D-003 producer-before-consumer ordering   /   D-004 DISP=(MOD,DELETE) idiom
# --------------------------------------------------------------------------

def _resource_pairs(text, **kw):
    ir = _ir(text, v2_fixes=kw.get("v2_fixes", False))
    ext = StaticContractExtractor(
        v2_fixes=kw.get("v2_fixes", False),
        v2_resource_order=kw.get("v2_resource_order"),
    ).extract(ir)
    return sorted(
        (ir.entities[c.subject_id].name, ir.entities[c.object_id].name)
        for c in ext.resource_contracts
    )


CONSUMER_FIRST = """//J JOB A
//USE EXEC PGM=X
//IN DD DSN=A.B.C,DISP=SHR
//MAKE EXEC PGM=X
//OUT DD DSN=A.B.C,DISP=(NEW,CATLG)
"""

PRODUCER_FIRST = """//J JOB A
//MAKE EXEC PGM=X
//OUT DD DSN=A.B.C,DISP=(NEW,CATLG)
//USE EXEC PGM=X
//IN DD DSN=A.B.C,DISP=SHR
"""


def test_d003_default_emits_contract_for_consumer_declared_before_producer():
    """Before: the file's own order contradicts the contract it is credited with."""
    assert _resource_pairs(CONSUMER_FIRST) == [("MAKE", "USE")]


def test_d003_v2_drops_consumer_before_producer_pair():
    assert _resource_pairs(CONSUMER_FIRST, v2_fixes=True) == []


def test_d003_v2_keeps_correctly_ordered_pair():
    assert _resource_pairs(PRODUCER_FIRST, v2_fixes=True) == [("MAKE", "USE")]
    assert _resource_pairs(PRODUCER_FIRST) == [("MAKE", "USE")]


def test_d003_can_be_disabled_independently():
    assert _resource_pairs(CONSUMER_FIRST, v2_fixes=True, v2_resource_order=False) == [
        ("MAKE", "USE")
    ]


def test_documented_limitation_no_cross_file_resource_contracts():
    """Scope limit (unchanged by V2): entity ids hash the artifact path, so a dataset
    produced in one file and consumed in another never forms one DATASET entity and
    no cross-file RESOURCE contract exists, even though the class docstring mentions it."""
    ir = _ir(PRODUCER_FIRST, v2_fixes=True)
    _r, other = JCLParser(v2_fixes=True).parse_lines(CONSUMER_FIRST.splitlines(), "other.jcl")
    for e in other.entities.values():
        ir.add_entity(e)
    for r in other.relations:
        ir.add_relation(r)
    ext = StaticContractExtractor(v2_fixes=True).extract(ir)
    assert all(
        ir.entities[c.subject_id].artifact_path == ir.entities[c.object_id].artifact_path
        for c in ext.resource_contracts
    )


PREDELETE = """//J JOB A
//PREDEL EXEC PGM=IEFBR14
//DD1 DD DSN=A.B.C,DISP=(MOD,DELETE,DELETE),SPACE=(TRK,0)
//MAKE EXEC PGM=X
//OUT DD DSN=A.B.C,DISP=(NEW,CATLG)
//USE EXEC PGM=X
//IN DD DSN=A.B.C,DISP=SHR
"""


def test_d004_default_treats_mod_delete_as_producer():
    """Before: a bogus PREDEL -> USE contract (and PREDEL -> MAKE none, MAKE is a producer)."""
    assert ("PREDEL", "USE") in _resource_pairs(PREDELETE)


def test_d004_v2_ignores_pre_delete_idiom():
    pairs = _resource_pairs(PREDELETE, v2_fixes=True)
    assert pairs == [("MAKE", "USE")]


@pytest.mark.parametrize("disp,is_producer", [
    ("(MOD,DELETE,DELETE)", False),
    ("(MOD,DELETE)", False),
    ("(MOD,CATLG)", True),      # MOD with a retained dataset still produces
    ("(MOD,PASS)", True),
    ("(MOD)", True),
    ("MOD", True),
])
def test_d004_scope(disp, is_producer):
    text = f"//J JOB A\n//S EXEC PGM=X\n//D DD DSN=A.B.C,DISP={disp}\n"
    ir = _ir(text, v2_fixes=True)
    produced = any(r.relation_type == RelationType.PRODUCES for r in ir.relations)
    assert produced is is_producer


def test_d004_can_be_disabled_independently():
    p = JCLParser(v2_fixes=True)
    p.v2_delete_disp = False
    _r, ir = p.parse_lines(PREDELETE.splitlines(), "t.jcl")
    assert any(r.relation_type == RelationType.PRODUCES and r.source.name == "PREDEL"
               for r in ir.relations)


def test_documented_tradeoff_d004_renaming_a_pre_deleted_dataset_is_not_flagged():
    """
    Trade-off of D-004 (development benchmark: -2 true positives, +0 false positives,
    DUSRSECJ and ESDSRRDS RENAME_OUTPUT_DATASET). v1.x flagged a rename of the
    DISP=(MOD,DELETE) dataset only *because* it treated the delete as a producer
    (a bogus contract). The oracle labels such renames DIFFERENT (final catalog),
    but RELIC has no 'deletes' contract, so V2 no longer sees them.
    """
    mutated = PREDELETE.replace(
        "//DD1 DD DSN=A.B.C,DISP=(MOD", "//DD1 DD DSN=A.B.C.MIG,DISP=(MOD"
    )
    assert _flagged(PREDELETE, mutated) is True
    assert _flagged(PREDELETE, mutated, v2_fixes=True) is False


def test_d003_d004_corpus_effect_only_removes_resource_contracts():
    """V2 may only REMOVE RESOURCE contracts relative to v1.1 on unaffected files (see
    test_v2_equals_v11_on_unaffected_corpus_files); here pin the known UNLDPADB case."""
    path = next((ROOT / "datasets").rglob("UNLDPADB.JCL"))
    text = path.read_text(errors="replace")
    assert ("STEP01", "STEP0") in _resource_pairs(text)
    assert ("STEP01", "STEP0") not in _resource_pairs(text, v2_fixes=True)


def test_legacy_and_v2_are_mutually_exclusive():
    with pytest.raises(ValueError):
        JCLParser(legacy_v1_0=True, v2_fixes=True)
    with pytest.raises(ValueError):
        RelicDetector(legacy_v1_0=True, v2=True)


def test_v2_detector_name_and_default_pipeline_unchanged():
    from relic_eval.detectors import all_detectors
    assert RelicDetector(False, v2=True).name == "relic_v2"
    assert "relic_v2" not in {d.name for d in all_detectors()}   # published results unchanged


def test_v2_equals_v11_on_unaffected_corpus_files():
    """
    On every corpus JCL file that has neither duplicate step names nor the
    D-002 constructs, V2 must extract exactly the v1.1 TEMPORAL and
    CONTROL_FLOW contracts, and its RESOURCE contracts must be a subset of
    v1.1's (D-003/D-004 only ever remove RESOURCE contracts).
    """
    import re
    checked = 0
    for path in sorted((ROOT / "datasets").rglob("*")):
        if path.suffix.lower() not in {".jcl", ".prc", ".proc"} or not path.is_file():
            continue
        text = path.read_text(errors="replace")
        if re.search(r"DSNAME=|DISP=\(,", text, re.IGNORECASE):
            continue
        res, _ = JCLParser().parse_lines(text.splitlines(), str(path))
        names = [t.name.upper() for t in res.tokens if t.operation == "EXEC" and t.name]
        if len(names) != len(set(names)) or any(
            t.operation == "EXEC" and not t.name for t in res.tokens
        ):
            continue
        jobs = sum(1 for t in res.tokens if t.operation == "JOB")
        if jobs > 1:
            continue

        def sig(**kw):
            ir = _ir(text, **kw)
            ext = StaticContractExtractor(v2_fixes=kw.get("v2_fixes", False)).extract(ir)
            return sorted(
                (c.contract_type.value, ir.entities[c.subject_id].name,
                 ir.entities[c.object_id].name, str(c.metadata.get("rc_threshold")))
                for c in ext.all_contracts
            )

        old, new = sig(), sig(v2_fixes=True)
        assert [x for x in old if x[0] != "RESOURCE"] == [x for x in new if x[0] != "RESOURCE"], path
        assert {x for x in new if x[0] == "RESOURCE"} <= {x for x in old if x[0] == "RESOURCE"}, path
        checked += 1
    assert checked > 20

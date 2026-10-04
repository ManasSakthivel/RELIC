"""
Regression tests for defects found during the October 2026 remediation
(docs/remediation/PRE_REMEDIATION_AUDIT.md, P5 and P10) and for the legacy
switch that reproduces the as-released v1.0.0 behaviour.
"""

import json
from pathlib import Path

import pytest

from legacy_contract.bcg.builder import BCGBuilder
from legacy_contract.contracts.model import ContractType
from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.risk.detector import RiskDetector, guard_weakened
from legacy_contract.static_analysis.extractor import StaticContractExtractor
from relic_eval.detectors import neutral_record

ROOT = Path(__file__).resolve().parents[2]

CONTINUED = """//J JOB A
//MAKE EXEC PGM=IEBGENER
//SYSUT2   DD DSN=WORK.A,
//         DISP=(NEW,CATLG,DELETE)
//USE  EXEC PGM=IEBGENER
//SYSUT1   DD DSN=WORK.A,DISP=SHR
"""


def contracts(text, legacy):
    _r, ir = JCLParser(legacy_v1_0=legacy).parse_lines(text.splitlines(), "t.jcl")
    return StaticContractExtractor(legacy_v1_0=legacy).extract(ir)


def test_ibm_continuation_recovers_resource_contract():
    assert len(contracts(CONTINUED, legacy=True).resource_contracts) == 0     # v1.0 defect
    assert len(contracts(CONTINUED, legacy=False).resource_contracts) == 1


def test_sequence_columns_do_not_leak_into_operands():
    line = "//S2 EXEC PGM=IEFBR14,COND=(4,LT)".ljust(72) + "00500019"
    _r, ir = JCLParser().parse_lines(["//J JOB A", "//S1 EXEC PGM=IEFBR14", line], "t.jcl")
    step = [e for e in ir.entities.values() if e.name == "S2"][0]
    assert "0050" not in step.attributes["operands"]


def test_cond_without_stepname_binds_all_previous_steps():
    text = "//J JOB A\n//S1 EXEC PGM=X\n//S2 EXEC PGM=X\n//S3 EXEC PGM=X,COND=(4,LT)\n"
    assert len(contracts(text, legacy=True).control_flow_contracts) == 1
    assert len(contracts(text, legacy=False).control_flow_contracts) == 2


def test_balanced_cond_capture():
    text = "//J JOB A\n//S1 EXEC PGM=X\n//S2 EXEC PGM=X,COND=((4,LT,S1),(8,GT,S1))\n"
    res = contracts(text, legacy=False)
    assert {c.metadata["operator"] for c in res.control_flow_contracts} == {"LT", "GT"}


def _bcg(text, legacy):
    _r, ir = JCLParser(legacy_v1_0=legacy).parse_lines(text.splitlines(), "t.jcl")
    return BCGBuilder().build(ir, StaticContractExtractor(legacy_v1_0=legacy).extract(ir))


@pytest.mark.parametrize("new,flag_v11", [("(8,LT)", True), ("(2,LT)", False)])
def test_threshold_change_detection(new, flag_v11):
    orig = "//J JOB A\n//S1 EXEC PGM=X\n//S2 EXEC PGM=X,COND=(4,LT)\n"
    mut = orig.replace("(4,LT)", new)
    for legacy, expect in ((True, False), (False, flag_v11)):
        rep = RiskDetector(legacy_v1_0=legacy).detect(_bcg(orig, legacy), _bcg(mut, legacy), neutral_record())
        assert (len(rep.risk_items) + len(rep.false_positive_candidates) > 0) == expect, (legacy, new)


def test_guard_weakened_semantics():
    class C:
        def __init__(self, t, op):
            self.metadata = {"rc_threshold": t, "operator": op}
    assert guard_weakened(C(4, "LT"), C(8, "LT"))      # bypass RC>4 -> RC>8: runs at RC 5..8
    assert not guard_weakened(C(4, "LT"), C(2, "LT"))  # bypass set grows: stronger
    assert guard_weakened(C(4, "GT"), C(2, "GT"))      # bypass RC<4 -> RC<2: runs at RC 2,3
    assert guard_weakened(C(0, "NE"), C(4, "NE"))


def test_legacy_mode_reproduces_v100_contract_counts_on_carddemo():
    root = ROOT / "datasets/carddemo/extracted"
    totals = {ContractType.TEMPORAL: 0, ContractType.RESOURCE: 0, ContractType.CONTROL_FLOW: 0}
    for f in sorted(root.rglob("*")):
        if f.suffix.lower() != ".jcl":
            continue
        res = contracts(f.read_text(errors="replace"), legacy=True)
        for c in res.all_contracts:
            totals[c.contract_type] += 1
    # Recorded with the unmodified code at commit 024a3f2 before any change.
    assert totals == {ContractType.TEMPORAL: 79, ContractType.RESOURCE: 3, ContractType.CONTROL_FLOW: 21}


def test_rq1_legacy_macro_excludes_vacuous_files():
    r = json.loads((ROOT / "results/rq1/rq1_independent.json").read_text())
    assert r["n_vacuous_files_excluded_from_macro"] == sum(1 for p in r["per_file"] if p.get("vacuous_no_contracts"))
    assert all(p["f1"] is None for p in r["per_file"] if p.get("vacuous_no_contracts"))

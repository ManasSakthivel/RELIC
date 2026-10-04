"""
Detectors must be blind to the mutation: they receive only the two JCL texts
and the artifact path, and their decision must not depend on the placeholder
MutationRecord that RiskDetector requires for its explanation text.
"""

import inspect
import uuid

import pytest

from legacy_contract.mutations.engine import FailureCategory, MutationOperator, MutationRecord
from legacy_contract.risk.detector import RiskDetector
from relic_eval.detectors import _bcg, all_detectors

ORIG = """//J JOB A
//S1 EXEC PGM=IEFBR14
//S2 EXEC PGM=IEFBR14,COND=(4,LT)
//S3 EXEC PGM=IEFBR14
"""
MUT = ORIG.replace("(4,LT)", "(8,LT)")
SWAP = """//J JOB A
//S2 EXEC PGM=IEFBR14,COND=(4,LT)
//S1 EXEC PGM=IEFBR14
//S3 EXEC PGM=IEFBR14
"""


def test_predict_signatures_carry_no_mutation_information():
    for d in all_detectors():
        params = list(inspect.signature(d.predict).parameters)
        assert params[:3] == ["original", "mutated", "path"], d.name
        assert not any(p in params for p in ("operator", "mutation", "site", "label", "truth"))


@pytest.mark.parametrize("legacy", [True, False])
@pytest.mark.parametrize("mutated", [MUT, SWAP])
def test_relic_decision_independent_of_placeholder_record(legacy, mutated):
    b0 = _bcg(ORIG, "x.jcl", legacy)
    b1 = _bcg(mutated, "x.jcl", legacy)
    decisions = set()
    for op in MutationOperator:
        rec = MutationRecord(str(uuid.uuid4()), FailureCategory.F3_RC_PROPAGATION, "x", op,
                             ["a", "b"], ["c"], "o", "m", 7)
        rep = RiskDetector(legacy_v1_0=legacy).detect(b0, b1, rec)
        decisions.add(len(rep.risk_items) + len(rep.false_positive_candidates) > 0)
    assert len(decisions) == 1

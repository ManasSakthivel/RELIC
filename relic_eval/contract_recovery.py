"""
RQ1 — contract recovery against oracle-derived facts, for all three contract
types RELIC extracts.

For each JCL job file, RELIC's extracted contracts are reduced to step-name
pairs and compared with facts computed independently by ``jcl_oracle``:

  TEMPORAL      RELIC  A PRECEDES B                 vs  consecutive top-level steps
  RESOURCE      RELIC  A PRODUCES_BEFORE_CONSUMES B vs  B reads data written by A
                                                        (baseline scenario simulation)
  CONTROL_FLOW  RELIC  B must not follow A on error vs  B's EXEC COND tests A's RC
                (IF/THEN/ELSE guards reported separately: outside RELIC's scope)

Granularity: top-level job steps (procedure steps are collapsed into the step
that invokes the procedure). Self-pairs are dropped. Micro-averaged
precision/recall/F1 over all pairs of a subject.

Output: results/final/contract_recovery.json
"""

from __future__ import annotations

import json

from loguru import logger

from jcl_oracle.judge import describe_file
from legacy_contract.contracts.model import ContractType
from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.static_analysis.extractor import StaticContractExtractor
from relic_eval.metrics import Confusion
from relic_eval.subjects import ROOT, get_subjects

logger.remove()
OUT = ROOT / "results" / "final" / "contract_recovery.json"


def relic_pairs(text: str, path: str, legacy: bool) -> dict[str, set[tuple[str, str]]]:
    _r, ir = JCLParser(legacy_v1_0=legacy).parse_lines(text.splitlines(), path)
    res = StaticContractExtractor(legacy_v1_0=legacy).extract(ir)
    names = {eid: e.name for eid, e in ir.entities.items()}
    out: dict[str, set[tuple[str, str]]] = {"TEMPORAL": set(), "RESOURCE": set(), "CONTROL_FLOW": set()}
    for c in res.all_contracts:
        a, b = names.get(c.subject_id, c.subject_id), names.get(c.object_id, c.object_id)
        if a == b:
            continue
        out[c.contract_type.value if isinstance(c.contract_type, ContractType) else str(c.contract_type)].add((a, b))
    return out


def evaluate() -> dict:
    result: dict = {"description": __doc__.strip().splitlines()[0], "subjects": {}}
    for subject in get_subjects():
        totals: dict[str, dict[str, Confusion]] = {}
        files_with_truth: dict[str, int] = {}
        per_file = []
        for f in subject.jcl_files:
            text = f.read_text(errors="replace")
            ap = subject.artifact_path(f)
            facts = describe_file(text, subject.proclib, subject.cobol_sources)
            truth = {
                "TEMPORAL": facts.order_pairs,
                "RESOURCE": facts.dataflow_pairs,
                "CONTROL_FLOW": facts.cond_pairs,
                "CONTROL_FLOW_INCL_IF": facts.cond_pairs | facts.if_pairs,
            }
            row = {"file": subject.rel(f)}
            for version, legacy in (("relic_v1_0", True), ("relic_v1_1", False)):
                pred = relic_pairs(text, ap, legacy)
                pred["CONTROL_FLOW_INCL_IF"] = pred["CONTROL_FLOW"]
                for ctype, t in truth.items():
                    p = pred[ctype]
                    c = totals.setdefault(version, {}).setdefault(ctype, Confusion())
                    c.tp += len(p & t)
                    c.fp += len(p - t)
                    c.fn += len(t - p)
                    row[f"{version}:{ctype}"] = {"tp": len(p & t), "fp": len(p - t), "fn": len(t - p)}
            for ctype, t in truth.items():
                if t:
                    files_with_truth[ctype] = files_with_truth.get(ctype, 0) + 1
            per_file.append(row)
        result["subjects"][subject.key] = {
            "n_files": len(subject.jcl_files),
            "files_with_oracle_pairs": files_with_truth,
            "micro": {v: {ct: c.as_dict() for ct, c in d.items()} for v, d in totals.items()},
            "per_file": per_file,
        }
    return result


def main() -> None:
    res = evaluate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()

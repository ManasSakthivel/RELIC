# JCL-SemBench label audit (workstream 1)

Date of audit: 2026-11-20 (UTC). Scope: all 180 pairs in `benchmarks/sembench/cases.jsonl`.
Original labels are untouched. Corrections are versioned in `benchmarks/final/sembench_v1_1/`.

## 1. Where the labels stand

| Expected | Oracle verdict | Validation status | Byte-identical | Count |
|---|---|---|---|---|
| CHANGING | DIFFERENT | validated (oracle + argument) | no | 67 |
| CHANGING | EQUIVALENT | oracle disagrees | yes | 15 |
| CHANGING | EQUIVALENT | oracle disagrees | no | 10 |
| CHANGING | UNDETERMINED | oracle abstains | no | 1 |
| PRESERVING | EQUIVALENT | validated | no | 74 |
| PRESERVING | EQUIVALENT | validated | yes | 10 |
| PRESERVING | DIFFERENT | oracle disagrees | no | 3 |

Totals: 93 CHANGING, 87 PRESERVING. 25 byte-identical pairs. 28 oracle disagreements, of which 15 are the byte-identical CHANGING pairs.

## 2. Root cause of the 15 contradictions (verified)

- All 15 pairs have `original.jcl` and `transformed.jcl` byte-identical (`cmp` returns equal for 15 of 15).
- Each carries a rationale describing an edit (e.g. `sembench_100`: "Changing stage data source."), and its equivalence argument concedes that the oracle reports EQUIVALENT.
- The generator (`benchmarks/sembench/build.py`) has no assertion that the transformed file differs from the original, so the intended edit was never applied and the label described a change that the artefact does not contain.
- Consequence: the labels are wrong for the artefact as published. The oracle is right about these bytes.

## 3. Corrections applied (v1.1)

- **C1 (applied, 15 pairs):** relabel CHANGING to PRESERVING. Evidence: byte equality. Confidence: high. This is an objective fact about the files, not an oracle opinion.
- Alternative (sensitivity, not primary): exclude the 15 pairs instead of relabelling. Both are reported in `results/final/statistics/label_correction_metrics.json`.

## 4. Not corrected (14 pairs, pending adjudication)

- 10 non-identical CHANGING pairs and 3 non-identical PRESERVING pairs where the oracle disagrees, plus one abstention (`sembench_172`).
- Sampled evidence: `sembench_117` changes `DISP=SHR` to `DISP=OLD`, and `sembench_165` changes `COUNT(100)` to `COUNT(10)`. Both are real edits, so the CHANGING label looks plausible and the oracle's EQUIVALENT verdict looks suspect. That is an observation about two cases, not a verdict on all 13.
- These cases need independent adjudication before any change. None has been made here. No practitioner has reviewed them.

## 5. Effect on metrics (recomputed from `results/sembench/predictions.jsonl`)

Original labels reproduce the published values (RELIC V2 MCC 0.324; normalized text B 0.525; plain text diff 0.176).

| Detector | MCC, original labels | MCC, v1.1 (C1 applied) |
|---|---|---|
| relic_v2 | 0.324 | 0.394 |
| normalized_text_B | 0.525 | 0.731 |
| textdiff | 0.176 | 0.482 |

Correcting the labels raises every detector, but the text baselines rise more. The gap RELIC V2 − normalized text B widens from −0.201 to about −0.337. The defective labels had been counting byte-identical pairs as missed changes, which penalised the text baselines. The published headline therefore understated the gap in RELIC's disfavour. This must be reported in the paper.

## 6. Limits

- The oracle is same-author and unvalidated (see `reports/v2/ORACLE_INDEPENDENCE_AUDIT.md`). The v1.1 labels are only as good as the oracle for the 14 pending cases.
- No independent human adjudication exists. Nothing here is human validation.

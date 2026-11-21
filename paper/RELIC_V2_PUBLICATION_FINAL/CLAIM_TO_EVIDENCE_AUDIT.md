> **Superseded (2026-11-21).** This audit describes an earlier draft that included a language-model comparison. The current claims and their checks are in `reports/final_go/FINAL_CLAIM_TO_EVIDENCE_AUDIT.md`.

# Claim-to-evidence audit (manuscript as of 2026-11-21, UTC)

Analysis types: **Frozen** = frozen published data, recomputed from committed predictions;
**Post hoc** = analysis chosen after results were known; **Derived** = arithmetic on other rows;
**Judgement** = author classification, not independently checked; **External, not blind** = same oracle, labels fixed by operator.
Source paths are relative to the repository root.

| # | Claim (manuscript location) | Evidence and metric | Source | Analysis type | Limitation |
|---|---|---|---|---|---|
| 1 | 15 CHANGING pairs are byte-identical (Abstract; VI) | `cmp` of original.jcl vs transformed.jcl, 15/15 equal | `benchmarks/sembench/cases/*` | Frozen | none on the fact itself |
| 2 | Correction C1 relabels those 15 to PRESERVING; originals kept (III.B) | labels in `benchmarks/final/sembench_v1_1/cases.jsonl` with `expected_outcome_original` | `benchmarks/final/label_corrections.csv`, `reports/final/scripts/label_correction_v1_1.py` | Post hoc (correction) | byte equality, not an oracle opinion |
| 3 | L0 values: RELIC MCC 0.324, text B 0.525, $\Delta$ $-0.201$ [$-0.301$, $-0.096$] (Table I) | confusion matrices from predictions | `results/final/statistics/sensitivity_three_way.json`, `paired_sensitivity.json` | Frozen (point) / Post hoc (interval) | our bootstrap interval differs from the original [$-0.299$, $-0.102$]; cause not established; endpoints provisional |
| 4 | L1, L2, L3 values and paired intervals (Table I) | same | same | Post hoc | L2 and L3 are post hoc scenarios; L3 not significant on the cluster test (8a) |
| 5 | Sign of the gap is the same in all four label sets (Abstract; RQ1). The abstract no longer claims the interval excludes zero in all four. | MCC difference negative in L0–L3 | same | Derived | depends on four sets chosen post hoc |
| 6 | Gap lies between $-0.350$ and $-0.163$ over all $2^{13}$ assignments of the 13 disputed cases, abstention 172 kept at original label (RQ1) | exhaustive enumeration on the L1 base | `results/final/statistics/bounds_and_dedup.json`, `reports/final/scripts/bounds_and_dedup.py` | Derived (exact) | point estimates only; the other 166 labels are unverified |
| 7 | Dedup (drop 25 identical), L1 base, n=155: $-0.319$ | same | `bounds_and_dedup.json` | Derived | — |
| 8 | Exact McNemar: $p=0.002, 0.002, 0.029, 0.314$ on L0–L3 (RQ1, text only) | exact binomial on discordant pairs (26/55, 26/55, 25/44, 35/45) | `paired_sensitivity.json` | Frozen | treats duplicated pairs and shared base programs as independent; anticonservative; reported for continuity only |
| 8a | Exact cluster-level randomisation test: $p=0.015, 0.002, 0.010, 0.089$ on L0–L3 (Table I, inference) | 2^16 swaps of the two detectors within each of 16 base programs | `results/final/statistics/robustness_checks.json`, `reports/final/scripts/robustness_checks.py` | Frozen (exact) | 16 clusters; not significant on L3 |
| 8b | MCC of all six detectors on L0–L3 (Table `tab:all`); RELIC V2 below text B and job-parameter text diff on L1–L3; above plain text diff on L2 (+0.009) and L3 (+0.059) | point estimates | `results/final/statistics/robustness_checks.json` | Frozen | point estimates only |
| 9 | Specificity: RELIC 0.977 (L0) to 1.000 (L2, L3); text 0.678–0.747 (Table I) | confusion matrices | `sensitivity_three_way.json` | Derived | — |
| 10 | RELIC's two L0 false positives are sembench_078 and 079, both unresolved (RQ1) | per-case predictions with labels | `results/sembench/predictions.jsonl`, `benchmarks/sembench/cases.jsonl` | Frozen | — |
| 11 | RELIC has no true positive the text baseline misses, in any label set (RQ2) | RELIC-only TP = 0 on L0–L3; every RELIC flag is a text flag | `reports/final/scripts/complementarity_checks.py` | Derived | on L1–L3 text recall is 1.000, so the result is guaranteed there |
| 12 | Text baseline recall is 1.000 on L1–L3 (RQ2) | confusion matrices | `sensitivity_three_way.json` | Derived | — |
| 13 | Of RELIC's 70 L0 misses, 15 are no-ops and the rest split as stated (RQ2) | categorisation of misses | `reports/recovery/ALGORITHM_IMPROVEMENT_REPORT.md` | Judgement | author categorisation |
| 14 | Sequential decomposition: $+0.025$, $+0.135$, $+0.007$ sum to $+0.166$ (Table II) | stepwise recomputation | `results/final/statistics/l3_decomposition.json`, `reports/final/scripts/l3_decomposition.py` | Post hoc, exact | order-dependent split; total order-independent |
| 15 | Isolated effects: 078+079 alone $+0.038$; ten CHANGING alone $+0.134$; adding 036 to the rename set gives net $+0.025$ (RQ3) | single-group relabelling | `results/final/statistics/step_name_sensitivity.json`, `l3_decomposition.json` | Post hoc | order-dependent; 036 alone about $-0.013$ |
| 16 | The ten CHANGING relabels account for about 81% of the L1-to-L3 narrowing; their effect equals the C1 correction ($-0.135$) in the opposite direction (RQ3) | $0.135 / 0.166$ | `l3_decomposition.json` | Derived | depends on step order; replaces an earlier claim that the effect exceeds every other single decision, which the data do not support |
| 17 | Ten CHANGING disputed cases are enqueue, catalogue and SYSPRINT cases, flagged by the baseline and not by RELIC (RQ3; Table III) | per-case diffs and predictions | `benchmarks/sembench/cases/*`, predictions | Frozen + Judgement | the classification is the author's |
| 18 | Oracle observables are execution, dataflow, final catalogue and termination; SYSPRINT, enqueue and catalogue membership are not observables (V-A) | oracle specification §3 | `docs/evaluation/ORACLE_SPECIFICATION.md` | Frozen (documentation) | the specification is the author's |
| 19 | Steps are identified by name, so renames give DIFFERENT by construction (Table III) | oracle specification §3 and §7 | same | Frozen (documentation) | a modelling choice |
| 20 | EQUIVALENT: no observable differs, and every step whose position, guard or presence changed is fully modelled (V-A) | oracle docstring (`jcl_oracle/__init__.py` line 18) | `jcl_oracle/__init__.py`, spec | Frozen (documentation) | the completeness condition does not cover disposition, SYSOUT or enqueue changes |
| 20a | Existing datasets default to KEEP in the simulator; catalogue membership is not compared beyond existence (V-A) | simulator defaults | `jcl_oracle/simulate.py` lines 16, 548–550 | Frozen (code) | — |
| 21 | Ten of 93 CHANGING labels (11%) lie outside the declared boundary (VII) | count of CHANGING disputed cases with EQUIVALENT verdict | `cases.jsonl` | Derived | "outside boundary" is the author's reading of the spec; overall share 10/180 (5.6%) |
| 21a | RELIC V2 reports no change on 55 of the 78 CHANGING pairs in L1 (VII) | FN count, L1 | `sensitivity_three_way.json` | Frozen | recall of this detector on this benchmark |
| 22 | Fourteen disputed labels: 10 outside the boundary, 2 identity-by-name, 1 opaque (abstention), 1 PARM text hashing (Table III) | classification | session classification; `docs/evaluation/ORACLE_SPECIFICATION.md` | Judgement | not independently checked; 036 remains open |
| 23 | Five appended-step pairs are a generator defect not yet in the register (VI) | prior audit | `reports/recovery/BENCHMARK_ORACLE_AUDIT.md` | Judgement | not yet in `reports/v2/DEFECT_REGISTER.md` |
| 24 | External run: RELIC precision 1.000, recall 0.952, MCC 0.874; text recall 1.000 (V-D) | external metrics | `results/external/` and `results/recovery/external_rerun/metrics.json` | Frozen, external not blind | same oracle; operator-determined labels |
| 25 | External pooled F1 difference $-0.022$, file-clustered $[-0.042,-0.008]$; repo-clustered $[-0.032,+0.004]$ (V-D) | stats reanalysis | `results/recovery/stats_reanalysis.json` | Frozen | repo clusters 7; file clusters non-independent |
| 26 | One operator rule matches 821 of 824 external labels (V-D) | labels by operator | `results/recovery/external_rerun/` | Derived | — |
| 27 | Byte-level reproduction from a clean clone of the frozen commit (Reproducibility) | `make reproduce` and comparison | `reports/recovery/REPRODUCIBILITY_AUDIT.md` | Frozen | Docker not built |
| 28 | Docker image does not build as written (Reproducibility) | configuration inspection; daemon not running | `reports/recovery/REPRODUCIBILITY_AUDIT.md` item 5 | Judgement (inspection) | build not attempted |
| 29 | LLM baseline (gpt-oss-120b, temp 0, both files shown) (Limitations) | raw responses and parse status | `results/final/llm/groq_gpt_oss_120b_raw.jsonl` | Post hoc, exploratory | see status in manuscript |
| 30 | No independent practitioner or held-out subject exists (Limitations) | project record | `reports/v2/review_package/` (zero responses) | Frozen | — |

## Open items before submission
- LLM section: status to be completed from the final scoring (`results/final/llm/`).
- Prior analysis: the earlier analysis of this benchmark reported uncorrected labels. Whether an erratum or correction note is needed is the authors' decision.
- Jackson and Ladd: Crossref returned surnames only; given names must be checked against the IEEE Xplore record before submission.
- Five appended-step defect: add to `reports/v2/DEFECT_REGISTER.md`.
- Figures: `fig1_mcc_and_overlap.pdf` (old populations) is no longer used; remove from the source tree or regenerate.

## Claims withdrawn in this revision
- "The paired interval excludes zero in all four label sets": the cluster-level exact test gives $p=0.089$ on L3.
- "Labelling them with the oracle's verdict changes the comparison more than any other single decision": the effect equals the C1 correction in size and opposite in sign.
- "The boundary decides a tenth of the labels": 10 of 93 CHANGING labels, and 10 of 180 overall.
- "Our data show this risk is not hypothetical": no decision-level data exist.
- "The Docker image does not build" (as an observed fact): the image was not built; inspection found no lock file.
- "Byte-for-byte reproduction" of intervals: the SemBench L0 interval differs from the published one.
- Bibliography entries for Ferrante et al. (1984) and Horwitz et al. (1988) corrected to Crossref venue data.
- Internal pre-registration file cited in the manuscript as a bibliography entry: removed (now "withheld for review" in text).

## Matched LLM subset (RQ4, exploratory, partial coverage)
| # | Claim (manuscript location) | Evidence and metric | Source | Analysis type | Limitation |
|---|---|---|---|---|---|
| 31 | The LLM run answered 155 of 180 pairs; the subset is exactly those pairs (RQ4; Limitations) | 155 distinct parsed verdicts, all CHANGING/PRESERVING | `results/final/llm/matched_subset_v1/frozen_raw_snapshot.jsonl` (sha256 in `manifest.json`) | Frozen | run stopped by the author at 155 to freeze outputs; not completed |
| 32 | The 25 unanswered pairs are all 7 pairs of four base programs plus 18 pairs with identifiers 119–173, so the subset is not a random sample or a clean prefix (RQ4). Subset holds 72 CHANGING and 20 byte-identical pairs; of 14 disputed cases, 13 are in the subset (130 is not) (RQ4) | list of missing IDs and base programs | `results/final/llm/matched_subset_v1/manifest.json`, `llm_matched_subset.py` output | Frozen | 12 of 16 programs covered |
| 33 | RELIC V2 and text B were scored on exactly the same 155 pairs from frozen predictions (RQ4) | every subset ID has a RELIC and text prediction (assert in script) | `results/sembench/predictions.jsonl` | Frozen | no RELIC re-run was needed; predictions are deterministic from committed files |
| 34 | MCC by system and label set, and paired $\Delta$MCC with cluster-bootstrap intervals and exact cluster-swap $p$ (Table IV) | recomputed from saved predictions | `results/final/llm/matched_subset_v1/matched_subset_scores.json`, `reports/final/scripts/llm_matched_subset.py` | Post hoc, exploratory | 12 clusters; denominators 155/155/142/154 |
| 35 | LLM has higher MCC than RELIC V2 and text B under every label set (Abstract; RQ4; Discussion) | Table IV | same | Post hoc | partial, one model, one prompt; not tuned |
| 36 | RELIC V2 is below text B on L1 ($p=0.008$) and L3 (not significant) on this subset | Table IV | same | Post hoc | — |
| 37 | Key handling: the scratch copy of the API key was removed; no key-shaped string is in the repository | file search (names only) | repository and scratchpad | Judgement (inspection) | the key appeared in chat and should be rotated by the user |

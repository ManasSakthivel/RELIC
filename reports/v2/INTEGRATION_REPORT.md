# RELIC V2 — Integration report (multi-agent sprint)

Branch `research/relic-v2-integration` (from `b690039`). Inputs: six agent reports —
`AGENT_1_METRICS_AUDIT.md`, `research/v2/LITERATURE_AND_NOVELTY_ASSESSMENT.md`,
`EXTERNAL_VALIDATION_PROTOCOL.md`, `AGENT_4_TECHNICAL_AUDIT.md`,
`paper/v2/REVIEW_AND_REVISED_DRAFT.md`, `AGENT_6_RELEASE_AUDIT.md`. All six completed.
Items I re-ran myself are marked **(re-run)**; everything else is as reported by the agent
that executed it.

## Answers to the critical questions

**A. Why does RELIC V2 score 0.980?** TP 442 / FP 0 / FN 18 / TN 106 (recomputed independently by
Agent 1 from the raw predictions: no discrepancy in 12 detectors × 4 populations). Gain over v1.1
(0.951) is a *file-level* effect: it comes from 7 files with repeated step names (v1.1 recall 0.391 →
0.766 there; elsewhere 392 → 393 TP). Fixes were developed on these same files, so the figure is
a development result.

**B. Why does the text-change diagnostic reach 0.998?** Its 2 FPs are both COND edits in `TXT2PDF1.JCL`.
All 460 positives are non-cosmetic text edits and 104 of 106 negatives are comment/MSGCLASS edits, so
the label DIFFERENT coincides with "a non-cosmetic text edit happened" on 564/566 mutants. The
paired bootstrap V2 − diagnostic is [−0.037, −0.003]: the trivial rule is *better* on this benchmark.

**C. Does RELIC give behavioural analysis beyond syntactic differences?** Not demonstrated by this
benchmark. RELIC does extract order/dataset/COND contracts, which a text diff cannot represent, but no
evidence here separates that from text-edit detection. The benchmark has no benign reorders, renames
or reformatting. Claim must be narrowed to "no false positives on cosmetic edits plus structural
contract recovery (TEMPORAL/CONTROL_FLOW exact on CardDemo)".

**D. Is the benchmark contaminated by development-time inspection?** Yes, for V2. CardDemo, OMP
and GenApp were all inspected while diagnosing D-001…D-004; mutator and oracle share a lexer
(`jcl_oracle.lexer`); one author wrote oracle, mutator, detector. v1.0/v1.1 results carry the same
caveat (v1.1 fixes were post hoc).

**E. Can RELIC be independently validated on unseen JCL?** Feasible in part (Agent 3): 4 verified
external candidates, none used in development — `IBM/zopeneditor-sample` (Apache-2.0),
`zowe/zowe-install-packaging` (EPL-2.0), `cschneid-the-elder/mapa` (MIT, synthetic parser-stress
data only), `yetacp/mvs_sysgen` (MIT fork, upstream license unverified). Verified pool ≈ 4 repos
→ weak cluster-level intervals. Agent 3 saw aggregate counts and fragments, so those repos are
"screened by aggregate", not blind. Independent ground truth needs a human relabelling sample (days–weeks) or real
z/OS/ZD&T (external partner). **Not done in this sprint: external validation remains pending.**

**F. What is the actual scientific contribution?** (Agents 2, 5.) Not a new detection algorithm.
Defensible: (i) an executable-oracle JCL change-risk benchmark methodology (no prior art found,
but search was incomplete: DBLP and Semantic Scholar were unavailable); (ii) scoped static
behavioural-contract extraction for JCL (incremental over specification mining / Rehearsal /
build-rule analysis); (iii) an audited negative result — a normalised text diff matches or beats the
detector on the benchmark — and a validity-threat catalogue.

**G. Claims to remove or narrow.** See `paper/v2/REVIEW_AND_REVISED_DRAFT.md` §claims table.
Main ones: "advantage = specificity on harmless edits" (reproduced by a trivial rule); "LLM subsample
is random / quota-limited" (false: 183 invalid outputs, positive-biased); LLM model/provider
(nvidia gpt-oss-20b in records vs Groq gpt-oss-120b in `paper.md`, `limitations.md`); "ten operators"
(nine evaluable); "independent oracle" (code-independent only); "v1.0.0 as released"
(legacy-mode code, not release checkout); selective CardDemo-only CI in the abstract (pooled interval
favours the text rule); "V2 significantly improves F1" (CI lower bound 0.003, development data).

**H. Minimum evidence for a credible submission.** (1) Frozen detector and oracle; a sealed,
repository-split external set with pre-registered metrics (protocol drafted). (2) Negative classes
a text rule cannot trivially win: benign reorders/splits, symbolic renames, PROC-parameter
changes, reformatting; report the normalised-text baseline. (3) Independent human audit of a random
oracle-label sample with agreement statistics. (4) A fair LLM re-run (one documented model,
retry policy for invalid output, full coverage). (5) Honest scope: JOB-card/PROC/IF/INCLUDE limits
stated. **All five are [PENDING EXPERIMENT].**

## Prioritised issues

| Pri | Issue | Source | Action this sprint |
|---|---|---|---|
| P0 | Benchmark label ≈ text-edit predicate (D-025, D-014) | Agent 1 | documented; manuscript narrowed in `paper/v2` |
| P0 | LLM model/provider and "random subsample" claims wrong | Agents 1,5,6 | **fixed** in hand-written README text and `docs/limitations.md`; generated README block (line 102) and `paper/paper.md` NOT changed (generator / research-lead scope) → release blocker |
| P0 | V2 numbers are development-only; fixes chosen on the same files | all | stated everywhere; test pins counts |
| P0 | Tests were circular for results (no pinned numbers) | Agent 1 | **fixed**: 10 pinned-confusion tests recompute from raw prediction records |
| P0 | Exceptions scored as "not flagged" (D-022) | Agent 4 | documented (0 `None` in V2 predictions); harness change deferred |
| P0 (generality) | Multi-job ordering (D-020), in-stream `//` data (D-021) **(re-run)** | Agent 4 | documented with corpus exposure; **not fixed** — would alter SPLIT_JOB results; needs ablation |
| P1 | External validation, stronger baselines, fair LLM re-run, related-work gaps | Agents 2,3,5 | protocol and drafts written; experiments pending |
| P1 | Unsupported-construct diagnostics (D-023), `static_bcg_E` duplicate (D-024) | Agents 1,4 | documented |
| P2 | New contract families, PROC/INCLUDE/IF parsing, UI, performance | — | not started |

## Release audit (Agent 6, re-run where noted)
Branch/HEAD and remote in sync; 439 tests passed at audit time; **449 pass after this sprint's added pinned-number tests (re-run)**; `make v2-eval`
byte-identical to committed (metrics + predictions); consistency check passes (re-run);
0 of 1277 historical `results/` files differ from `aee2309`; no secrets found; 2 old large tracked files
(33.8 MB zip, 7 MB GIF; pre-existing). Open blockers: R-1 `paper/paper.md:162` still says Groq 120b;
R-2 README never mentions V2; R-3 version fields disagree (0.1.0/1.1.0/v1.0.0); R-4 Dockerfile/compose
stale; R-5 `v2_run_info.json` dirties the tree on each run; R-6 dataset licences partly unverified;
R-7 `make setup` and full `make reproduce` not re-run on this HEAD (full reproduction was run on `d79d449`).

## Manuscript (`paper/v2/`)
Full LaTeX tree created beside the untouched originals; numbers copied from
`results/v2/v2_metrics.json` / `results/final/metrics.json`; `[PENDING EXPERIMENT]` marks nine missing
evidences. **Not compiled** (no TeX on this machine; static checks only).
Bibliography: only entries verified via Crossref/arXiv are in `.bib` (25 in `research/v2/`);
unverified items (e.g. Sadiq data-flow paper, DeMillo 1978, McKeeman 1998, DECLARE) are not cited.

## Verdict
**CONDITIONAL GO — for an honest benchmark/negative-result/validity-audit submission only after the
pending experiments; NO-GO for any claim that RELIC V2 outperforms baselines or is validated.**
Reasons: arithmetic and reproducibility are sound, but the benchmark cannot distinguish RELIC
from a trivial rule, V2 is tuned on its evaluation data, there is no held-out set, no independent
oracle audit and no fair LLM comparison.

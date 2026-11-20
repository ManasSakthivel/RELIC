# Pre-registration for the recovery analyses (written before any hybrid metric is computed)

**Honest status.** The aggregate SemBench and external results were already known when this was written (they are in the sprint report and in `CANONICAL_NUMBERS.json`, generated from the committed prediction files). Nothing below can therefore be called *confirmatory* with respect to those data. What this file fixes is the **analysis rules**, so that no rule can be chosen after seeing which one flatters RELIC. Everything beyond these rules is labelled **exploratory**. Confirmatory evidence requires data no one has opened (see the held-out item at the end).

## Fixed definitions

- Detectors are binary; no score or confidence exists, so there is one operating point per detector and **no precision-recall curve or threshold sweep is computable**. No such figure may be drawn.
- "Normalized text baseline": SemBench = `normalized_text_B` (the comparator behind the reported MCC 0.525); external = `textdiff_ignore_job_parameters` (the comparator behind the reported F1 0.9978). The other text variants are reported as sensitivity.
- Truth = oracle label (SemBench: `expected_outcome`; external: `truth`). The oracle is same-author and unvalidated (reports/v2/ORACLE_INDEPENDENCE_AUDIT.md).

## Populations (all reported; none is dropped from the paper)

1. `ALL_180` — as originally frozen and reported (primary for continuity).
2. `EXCL_25_IDENTICAL` — pre-declared sensitivity (25 byte-identical pairs).
3. `EXCL_15_NOOP_CHANGING_ONLY` — removes only the 15 pairs whose label is provably wrong (CHANGING with identical files).
4. `CLEAN_CORE` — additionally removes oracle disagreements and the abstention.
5. External: `EVALUABLE` (n = 824), pooled and per repository.

## Fixed hybrid rules (no parameters, so nothing to tune)

- `UNION`: flag if RELIC **or** text flags.
- `INTERSECTION`: flag if RELIC **and** text flag.
- `FAST_TRACK` (text-then-RELIC): text flags every candidate for review; items that RELIC also flags are accepted without human review; all other text-flagged items are reviewed by a human who is assumed correct. Reported cost: items reviewed, and wrongly accepted items (RELIC false positives among accepted). Reported benefit: reviews avoided = |RELIC ∧ text| / |text-flagged|.

No other combination may be added to the confirmatory-style table. Any further combination is labelled exploratory and counted in the number of comparisons reported.

## Hypotheses and decision rules

- **H1 (original):** RELIC V2 has higher MCC than the normalized text baseline. *Rejected if* the paired difference in MCC (cluster bootstrap on `base_id`, 10,000 resamples, seed 20261004) has a 95% CI entirely below zero or the point estimate is negative in the primary population.
- **H2 (complementarity):** RELIC detects true changes the text baseline misses. *Rejected if* RELIC-only true positives = 0 in the primary populations.
- **H3 (triage precision):** RELIC's flagged set has precision ≥ 0.95. *Rejected if* the Wilson lower bound < 0.90 in the external pooled set or any repository with ≥ 20 RELIC-flagged items.
- **H4 (review-effort saving):** FAST_TRACK avoids ≥ 30% of reviews at ≤ 1% wrongly accepted. *Rejected otherwise.* The 30% and 1% values are set here because a smaller saving would not justify maintaining a second analyser; they are not tuned.
- **H5 (explanatory value):** RELIC's contract output identifies the violated rule on its true positives. *Not testable from binary predictions*; requires an explanation-fidelity audit and is reported as **untested** unless that audit is run.

## Multiple comparisons
Paired tests are reported with Holm correction over all comparisons actually run, and the count of comparisons is stated.

## Not done, and what would be needed
- **Held-out confirmation:** a corpus never opened during development and a frozen detector. None exists.
- **Independent oracle validation:** the 60-case package (`reports/v2/review_package`) has zero returned human labels. It must never be described as completed validation.

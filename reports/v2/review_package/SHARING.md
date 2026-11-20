# What to hand to reviewers (and what never to hand over)

**Give each reviewer exactly:** `RUBRIC.md`, `cards/` (R001-R060), `responses_template.csv` (renamed
`responses_<REVIEWER-ID>.csv`). Optionally `blind_review_form.csv` (same case list, no labels).

**Never give to reviewers:** `KEY_DO_NOT_SHARE.csv`, `make_sample.py`, `sampling_frame.json`,
`experiments/`, `cards.jsonl` (same content as the cards but includes no labels - safe, but unnecessary),
`compute_agreement.py` output from any `--compare-oracle` run, `../ORACLE_INDEPENDENCE_AUDIT.md`,
`../INDEPENDENT_REVIEW_PACKAGE.md`, `results/final/**`, or any RELIC / oracle output.

Status: **PENDING - no reviewer has rated anything.** All response/adjudication files in this directory
are empty templates. See `../INDEPENDENT_REVIEW_PACKAGE.md` for procedure and statistics.

# Reviewer response matrix (final)

One independent adversarial reviewer (general-purpose agent, read-only, no access to earlier audits or the criteria). Verdict: ACCEPT WITH REQUIRED REVISIONS. Its single largest risk: rejection as out of ResponsibleSE scope. Reviews are AI-assisted; they are not human peer review. Its citations were from memory and were not verified online unless stated.

| # | Objection | Verified? | Response | Status |
|---|---|---|---|---|
| 1 | Novelty: observability effect is Staats 2011/2012 territory | Yes (concept); concession in paper | Background now says the effect is not new; the claim is the per-case accounting | Fixed in text |
| 2 | Uncited closest work: Schuler and Zeller (coverage/observation) | Not verified online | Not added; a citation would need a Crossref check first | Open (minor) |
| 3 | ResponsibleSE relevance thin: "responsib*" only in keywords | Yes | Added one assurance sentence (Discussion). The paper's subject is still a detector/benchmark comparison | Not resolved; drives NO-GO |
| 4 | Category: Short WIP is right; "WIP" implies unfinished | Partly | Category kept; the paper calls the study a completed bounded analysis with preliminary evidence | Partly resolved |
| 5 | Overclaim "measured value depends on observable boundary" as general law | Yes | Scoped to "In this case study" | Fixed |
| 6 | "ranking is robust; size is not" beside L3 p=0.089 | Yes | Retitled "sign is consistent; size is not"; L3 non-significance stated | Fixed |
| 7 | Figure caption "ranking is stable" | Yes | Replaced with sign statement | Fixed |
| 8 | "uninterpretable" overclaim | Yes | Softened | Fixed |
| 9 | "conservative for RELIC" backwards | Partly (it sets the bar high for RELIC; but the choice is post hoc) | Stated as not favouring RELIC, with the post hoc caveat | Fixed |
| 10 | "lesson is not that one decision dominates" contradicts 81% attribution | Yes | Sentence removed | Fixed |
| 11 | LLM paragraph one-sided | Yes | Best case 0.890 and 21/25 CHANGING skew added to limitation | Fixed |
| 12 | Decomposition +0.025 should be +0.024 | Yes (unrounded 0.02446) | Corrected in table and text | Fixed |
| 13 | Abstract p≤0.015 vs 0.0154 | Yes; 0.0154 rounds to 0.015 | Kept; the reviewer's "0.016" would be a wrong rounding | Not changed (correct as is) |
| 14 | Cross-reference sec:stats points to wrong section | Yes | Now sec:labels | Fixed |
| 15 | Undisclosed benchmark authorship (12 synthetic programs authored by the group; 30-pair base; 7 corpus pairs) | Yes (counts) | Disclosed in Methods | Fixed |
| 16 | sembench_174, 175: RELIC flags nothing | Yes (flags false on all versions); "zero contracts" not verified | Not claimed; flagged for the record | Open (disclose only) |
| 17 | Two bootstrap outputs disagree (paired_sensitivity.json) | Yes; that file uses Python random and is superseded | Excluded from the archive; not cited | Fixed (by exclusion) |
| 18 | Ferrante citation should be TOPLAS 1987 | Yes (Crossref: TOPLAS, 1987, DOI 10.1145/24039.24041) | Replaced | Fixed |
| 19 | CITATION.cff at repository root names the author and a public v1.1.0 release | Yes (file exists); public status not confirmed | Root not in archive; "not published externally" needs the user to confirm the release status | Open (user) |
| 20 | Archive contains uncited files and internal audit files | Yes (earlier build) | Rebuilt as v4 with cited files only | Fixed |
| 21 | Page rendering not checked | Pages counted (6) via pypdf, not visually | Not visually verified | Open (minor) |
| 22 | External run and LLM predictions not supplied to the reviewer | Yes | Reviewer limitation, not a paper defect | Noted |

Summary: 15 fixed or resolved, 1 partly resolved, 4 open or noted, 1 scope objection not resolved (item 3, which drives the decision).

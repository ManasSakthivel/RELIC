# GO criteria for the narrowed short paper (ResponsibleSE 2027)

Written 2026-11-21 (UTC ~02:30), after the independent adversarial review was launched and before it reported. The reviewer was given the official category text and the manuscript only; it was not given these criteria. Criteria are not edited after the review result is known; any change is logged below.

## Scope of the claim
The paper is a negative, preliminary evaluation of one benchmark (JCL-SemBench, 180 pairs) with one oracle, both built by the same group. It claims: (1) an exact per-case accounting of the label defects and the oracle's observable boundary; (2) that on this benchmark a normalized text baseline has higher MCC than RELIC V2 under all four label sets; (3) that the size of that gap depends on label choice. It does not claim superiority of any detector, general invalidity of the oracle, independent validation, or generalisation.

## Category
Short paper, Work-in-progress with preliminary results (ResponsibleSE CFP: "Short papers (4-6 pages)", "Work-in-progress papers (with/without preliminary results)"). Rationale: the study is a completed, bounded negative result on one benchmark, but its evidence is preliminary because labels are not independent. Research Paper (6-8 pp) was rejected as the category because the evidence is closed-loop and the contribution is narrow. Position/Reflection was rejected because the paper's weight is empirical accounting, not an argued position.

## Criteria (all must pass for GO)
| ID | Criterion | Evidence | Status at writing |
|---|---|---|---|
| G1 | Length: 4–6 pages in IEEE conference format, references included (conservative reading) | `paper/RELIC_V2_PUBLICATION_FINAL/main.pdf` page count | 6 pages (pass) |
| G2 | Template: `\documentclass[conference]{IEEEtran}` | `main.tex` line 1 | pass |
| G3 | Anonymity: no author names, affiliations, repository links, paths or identifying metadata in text, PDF metadata or figures | text scan; PDF and figure metadata scan | pass at writing |
| G4 | Scope: the contribution is framed as responsible evaluation and benchmark construct validity; no detector-superiority claim | manuscript read; adversarial review item 2 and 4 | to be confirmed by review |
| G5 | Every number in the paper matches the committed outputs | `reports/final_go/verify_manuscript_text.py` (tie-safe interval and p-value check, exit 0); `verify_manuscript_numbers.py` (32 PASS, no failures) | pass |
| G6 | Prior analysis disclosed without a false citation | Threats (Internal) paragraph; no citation | pass; no external publication found in the repository |
| G7 | z/OS PARM equivalence for case 036 stated as unchecked | Section V-E / Table V text | pass |
| G8 | LLM comparison absent from abstract and central contribution; one bounded limitation sentence retained | abstract, RQs, limitations | pass |
| G9 | No placeholders, TODOs, "pending" markers or internal file names in the paper | source scan | pass at writing |
| G10 | Adversarial review verdict is ACCEPT as short WIP, or ACCEPT WITH REQUIRED REVISIONS whose revisions are completed | review report | pending |

## Blocking conditions (any one blocks GO)
- The review verdict is REJECT, or it finds a factual error in the numbers or in the description of the oracle.
- The review finds a sentence that claims superiority of RELIC or general invalidity of the oracle, and it cannot be fixed by rewording within 6 pages.
- The category is judged wrong by the review and the correct category cannot be chosen within the same text.
- Submission portal status cannot be confirmed open before the deadline (HotCRP sign-in page states the deadline as Saturday 21 Nov 2026, 6:59:59 AM EST, i.e. 11:59 UTC; the workshop page says AoE 20 Nov).

## Not required for GO (disclosed, not blocking)
- Independent labels, held-out corpus, human validation (none exists; the paper says so).
- Completion of the 25 LLM pairs (LLM is not in the claim).
- Commit or push of the repository (requires the user's approval, which has not been given).
- z/OS equivalence of the two PARM quoting forms (disclosed as unchecked).

## Change log
- 2026-11-21: criteria written. No edits after review result.

## Review result and evaluation (2026-11-21, after the review reported)
- G1 PASS: 6 pages including references.
- G2 PASS: IEEEtran conference class.
- G3 PASS for the manuscript, PDF and figure metadata. Risk: the repository root `CITATION.cff` names the author and a public v1.1.0 release. The root is not in the archive, and the archive was rebuilt from cited files only.
- G4 FAIL in substance: the reviewer found "responsib*" only in the keywords. The body is a detector comparison; the responsibility argument is one added sentence. This is a scope-fit failure, not a wording fix.
- G5 PASS: `verify_manuscript_text.py` exit 0; `verify_manuscript_numbers.py` 32 PASS, no failures.
- G6 PASS as wording: the prior analysis is described as internal and uncited; the repository `CITATION.cff` mentions a public release, so "not published externally" is not confirmed for the software release. Open.
- G7 PASS: 036 z/OS equivalence is stated as unchecked.
- G8 PASS: LLM removed from abstract and central claims; bounded limitation kept.
- G9 PASS at writing.
- G10 FAIL: review verdict is "ACCEPT WITH REQUIRED REVISIONS", and its main risk is that the paper is rejected as out of scope. The revisions were made (overclaims softened, decomposition corrected to +0.024, Ferrante citation corrected to TOPLAS 1987, benchmark authorship disclosed, sec cross-reference fixed). The scope risk remains.

Decision recorded in FINAL_GO_REPORT.md: NO-GO for ResponsibleSE 2027 on scope fit.

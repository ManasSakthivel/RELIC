# Final review report

Scope: the anonymous manuscript (paper_anonymous.pdf) and camera-ready source, after the final revision pass.

## What was checked
- Factual corrections: Table 3 row 1 now reads "25 byte-identical pairs, including 15 labelled CHANGING". Row 3 now reads "13 non-identical oracle disagreements and one abstention without independent adjudication", and the total of 28 remains in Table 1.
- L3 statistics: the paragraph now states that the exact test does not reject (p = 0.089), that the bootstrap interval excludes zero, and that the exact test is primary, fixed before the L3 result was inspected.
- Oracle wording: the oracle is described as the only automated cross-check, shared in authorship, with no independent human validation.
- Numbers: this revision changed no statistic. The numbers were checked against saved outputs in the earlier pass; verify_manuscript_text.py and verify_manuscript_numbers.py were NOT re-run on the new sources in this pass.
- References: the 13 DOIs in REFERENCE_VERIFICATION.md match references.bib exactly. Record-level checks were done in an earlier session; they were not repeated in this pass. The 14th entry (jackson1994) was re-added with its DOI.
- Anonymity: passes the checks in ANONYMITY_AUDIT.md.

## Findings from the last independent reviewer (before this revision)
Verdict was "accept with required revisions". Status of each required revision:
1. Abstract duplicate-group wording: fixed earlier ("Forty-six pairs form 21 duplicate groups").
2. Oracle scope of the ten labels: fixed. The five CATLG-to-KEEP labels are described as ones the oracle does not distinguish, and whether they are label errors is not decided.
3. Repository reference: removed from the PDF.
4. Kapoor citation: narrowed to general leakage.
5. LLM bounds: stated (0.603 and 0.890 against text B 0.731).
6. Recompile and page count: done (4 pages). The decomposition artifact field "L3_recomputed_gap" holds the L1 value (−0.3362); it is not cited in the paper but is a defect in the artifact, left unchanged as historical evidence.
7. Responsible-role column and miss-type breakdown: added to Table 3 (16 disposition, 12 condition, 12 return-code, 10 dataset, 5 reorder misses).

## Not re-run in this pass
- A new independent reviewer on the final text was not run. The edits since the last review are the wording items above and the author block.
- Visual rendering was completed in a later pass (see BUILD_LOG.md). Table II was moved and reformatted; Table III sits at the top of page 4 rather than directly under its paragraph.

## Remaining critical or major issues
- None known for the anonymous manuscript.
- Major: the 151 "validated" labels rest on the same group's oracle and written arguments; this is disclosed, not resolved.
- Major: the responsibility contribution is a framework with two of five dimensions not yet done (independent scrutiny, decision consequences). Disclosed.
- Minor: reference claims are checked at title level only.

# Final submission readiness — ResponsibleSE 2027 short paper (WIP)

Checked 2026-11-21 (06:xx UTC; cutoff 11:59:59 UTC same day per the HotCRP deadline). Nothing committed, pushed, uploaded or submitted.

## Decision
The manuscript is ready for a human author to submit, subject to the items in "Before you submit" below. Those items are outside the manuscript itself.

## Acceptance criteria
| Requirement | Status | Evidence |
|---|---|---|
| Scientific scope | PASS | Claims limited to a preliminary case study; framework marked proposed; no validation claimed |
| Numerical integrity | PASS | verify_paper_numbers.py: 81 passed, 0 failed, exit 0 |
| Statistical interpretation | PASS | Exact cluster test primary; L3 described as p = 0.089 with bootstrap discrepancy disclosed |
| LLM comparison | PASS | All LLM values removed; one sentence states the run was excluded (coverage 155/180, non-random) |
| Deduplication claim | PASS | Now "little effect on L1" (−0.3375 vs −0.336); attribution to duplicates removed |
| L3 interpretation | PASS | Consistent in abstract, contributions, results, limitations, conclusion |
| L1 terminology | PASS | "no-op-adjusted baseline", "analytical adjustment, not ground truth"; no "corrected ground truth" |
| Script defect | PASS, disclosed | Original kept; corrected script and regression check; paper not affected (see provenance) |
| Groq output diff | PASS, disclosed | Two appended records match the frozen snapshot; no paper result depends on them |
| Rounding | PASS | Three decimals; four where a boundary was involved; one error fixed (0.665 → 0.666) |
| Novelty | PASS | "preliminary, non-systematic search"; no "first" or "no prior work" claims |
| ResponsibleSE framing | PASS | Section V states five accountability questions and the risk of unreviewed "no change" verdicts; cost not measured |
| References | PASS, limited | 14 entries, all cited, keys consistent. Verified against Crossref/arXiv in an earlier session; not re-verified now (offline); title-level claims only |
| LaTeX compiles | PASS | Both builds exit 0; no overfull/undefined warnings |
| Page count | PASS | Anonymous 4 pages; author-identified 5 pages (within 4–6) |
| Visual inspection | PASS, partial | Anonymous PDF: all four pages rendered and viewed; Table II checked at zoom. Author PDF: pages 1 and 5 viewed; pages 2–4 are the same body reflowed (not re-viewed). Page 5 holds only two references, cosmetic |
| Anonymous PDF | PASS | Text and metadata scan: no names, affiliation, GitHub, paths, LLM terms. Metadata: Creator "LaTeX with hyperref", Producer xdvipdfmx, no Author/Title |
| Author PDF | PASS, pending confirmation | Names and designations from supplied profile text; see items below |
| Provenance | PASS | EVIDENCE_PROVENANCE.md with hashes and defects |
| Final red-team review | PASS, with issues | See "Remaining issues" |

## Final files (this folder)
- `ResponsibleSE2027_Anonymous_Submission.pdf` — submission PDF (4 pages).
- `ResponsibleSE2027_Author_Identified.pdf` — camera-ready PDF (5 pages). Not for review.
- `ResponsibleSE2027_Final_Manuscript.tex` — single LaTeX source; `\AnonFlag` switches author block and software sentence.
- `ResponsibleSE2027_Final_References.bib` — 14 entries.
- `build.sh` — regenerates both PDFs from the single source (`build_anonymous.tex` and `build_author_identified.tex` are generated, not hand-edited).
- `verify_paper_numbers.py` and `verify_paper_numbers_output.txt` — numerical verifier and its output.
- `EVIDENCE_PROVENANCE.md`, this file.

## Remaining issues
Manuscript (none critical):
1. Author PDF: the last two reference entries sit alone on page 5. Cosmetic.
2. Reference claims were checked at title level only; a full-text read is recommended before camera-ready.
3. The L1 "no-op-adjusted" set and the oracle-derived L3 both depend on the same group's oracle. Disclosed in the paper; cannot be resolved without practitioner labelling.
4. The 151 "validated" pairs are validated only by the same group's oracle and written argument. The paper says so.
5. Deduplication rule (first ID per group) is one choice; other rules were not tested.

Outside the manuscript (must be handled by the human author):
6. **Key handling.** A full-length key-format string was checked for across the working tree and all git history: none found. The `gsk_` matches in the audit report and in these notes are descriptions of the scan pattern, not keys. The Groq key pasted into chat earlier should still be rotated, since it was shared outside the repository.
7. **Author identity (resolved by the author).** The author confirmed "Rajashree Shettar" as the intended person; the author PDF uses that name. Designations and emails come from supplied profile text, not live RVCE pages (HTTP 403).
8. **Working-tree changes.** The Groq raw file (two appended records) and several tracked files show modifications. Decide what to commit; nothing has been committed.
9. **HotCRP.** The portal page showed only a sign-in form. Open/closed status and the deadline (11:59:59 UTC today per HotCRP, equivalent to 20 November AoE per researchr) must be confirmed by someone with an account.
10. **Artifact.** No anonymised artifact exists. The anonymous paper states this. If the venue requires one, it must be created before submission.

## Before you submit
- Read the anonymous PDF once, end to end.
- Confirm the deadline and that submissions are open in HotCRP.
- Rotate the Groq key and redact the tracked report file (item 6).
- Upload only `ResponsibleSE2027_Anonymous_Submission.pdf`. Do not upload the build folder or any `build_*` file.

THE MANUSCRIPT IS FINALIZED AND READY FOR HUMAN SUBMISSION TO RESPONSIBLESE 2027. Items 6–10 must be handled by the human author before submission.

# Anonymity audit (double-blind)

The CFP says both "single-anonymously" and "double-blind". Double-blind is treated as binding for the anonymous PDF.

## paper_anonymous.pdf (submission)
| Check | Result |
|---|---|
| Author block | "Anonymous Submission / Author details withheld for double-blind review" |
| PDF metadata | Creator "LaTeX with hyperref", Producer "xdvipdfmx"; no Author, Title or Subject |
| PDF text | no author names, no affiliation (RVCE and Bengaluru absent), no emails, no repository URL, no machine path, no "Manas" |
| Figures | none |
| Acknowledgements | none |
| Self-citation | none |
| Repository | described as "an anonymised artifact (URL withheld for review)" |

## paper_camera_ready.pdf (after acceptance only)
Contains the verified author names, affiliation and institutional emails (see AUTHOR_METADATA_VERIFICATION.md). It is not for review. The PDF metadata still has no author field; the camera-ready author block is typeset text only.

## Source-level risks in the anonymous package
- `main.tex` (the earlier source, kept for history) names no authors but its build history is in the folder. It is superseded by `main_anonymous.tex` and must not be submitted.
- `backup_before_final_revision/` contains the previous PDF and source. Not part of the submission.
- Build logs (`build_*.txt`) and the scratchpad folders contain local paths. Do not upload the working folder; upload only `paper_anonymous.pdf`.
- The repository root `CITATION.cff` names the author. It must not be included in any artifact.

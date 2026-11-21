# RELIC V2 — final decision for ResponsibleSE 2027

Date: 2026-11-21 (UTC ~03:00). Nothing committed, pushed, uploaded or submitted.

## Decision: NO-GO — venue fit and contribution insufficient for ResponsibleSE 2027

The manuscript is numerically sound and technically defensible as a short, bounded, negative evaluation. It is not a good fit for ResponsibleSE 2027, and I am not manufacturing a GO. Reasons:

1. **Scope fit (decisive).** ResponsibleSE's scope is "understanding of responsibility in the software engineering domain, comprising software design, processes, and products." The paper's subject is a detector comparison and its benchmark labels. The word "responsibility" appears only in the keywords; the responsibility argument is one added sentence. The independent reviewer rated this its largest risk and predicted rejection on that basis. Fixing this would need a different paper (about the responsible use of automated assurance claims), not a rewording.
2. **Contribution is narrow.** The effect that oracle observables bound verdicts is already established in oracle-observability work (Staats et al., ICSE 2011, 2012). The new part is an exact per-case accounting for one benchmark built by the same group. Useful, but thin for a responsibility venue.
3. **Evidence is closed-loop.** One benchmark, one oracle, same group, no independent labels, no held-out corpus, no human validation. The paper states this, which is correct, but it limits what a reviewer can accept.

What holds: the numbers reproduce (text verifier exit 0; 32 numerical checks PASS); the claims were narrowed and overclaims were corrected after review; the category (Short paper, WIP with preliminary results) is the right one for this evidence.

## Verified facts
- Manuscript: 6 pages including references; IEEEtran conference class; no identity strings in text, PDF or figure metadata.
- `verify_manuscript_text.py`: failures 0. `verify_manuscript_numbers.py`: 32 PASS, no failures.
- Deduplicated L1 gap −0.338; leave-one-program-out −0.364 to −0.313; worst-case L1 LLM 0.603 vs text B 0.731; best case 0.890.
- Decomposition step +0.024 (unrounded 0.02446).
- Ferrante et al. citation corrected to ACM TOPLAS 1987 (Crossref verified).

## Venue facts
- Categories (official CFP): Research Papers 6–8 pages; Experience Reports 6–8; Short papers 4–6 with WIP (with/without preliminary results), exemplar, vision, position/reflection, interactive tutorial.
- Format: IEEE conference template. Double-blind: "Please don't include author names and identifying information in the paper."
- Deadline: CFP says Fri 20 Nov 2026 AoE; HotCRP sign-in page says "Saturday Nov 21, 2026, 6:59:59 AM EST" (11:59 UTC today). I could not log in, so portal status is unverified.

## Open items (disclosed; not all blocking)
- The repository root `CITATION.cff` names the author and a v1.1.0 release. Whether that release is public is unconfirmed, so "not published externally" for the earlier internal analysis needs your confirmation.
- Two cases (sembench_174, 175): RELIC flags nothing. Not analysed further.
- Not visually checked: page rendering (page count via pypdf only).
- Not verified online: Schuler and Zeller (ICST 2011) suggested by the reviewer.
- z/OS equivalence of the two PARM forms in case 036: unchecked.
- External run numbers and LLM predictions: not re-verified in this final pass.

## Artifacts
- Manuscript: `/Users/manassakthivel/Desktop/RELIC-RECOVERY/paper/RELIC_V2_PUBLICATION_FINAL/main.pdf`
- Anonymised archive (48 cited files; excludes internal audits, root `CITATION.cff`, superseded results): `<SCRATCHPAD>/supplementary_anonymised_v4.zip`
- Older archives `supplementary_anonymised.zip` and `_v2.zip` in the same folder include internal documents or uncited files. Do not use them.

## What would change the decision
- Not a revision of this paper. A GO for ResponsibleSE would need a new paper whose subject is responsible evaluation of automated assurance (for example, what a "no change" verdict licenses a modernisation team to do), with independent labels. If you want to keep ResponsibleSE as the only target, this is a NO-GO for the current manuscript.
- Alternatively, this manuscript is a candidate for a benchmarking or negative-results venue. That would be a different target from the one you set, so I have not switched to it.

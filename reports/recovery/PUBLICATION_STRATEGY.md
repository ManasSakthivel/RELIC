# RELIC V2 publication strategy

Checked 2026-11-20 (all "checked" dates below are this date). Sources: official conf.researchr.org / msrconf.org pages. Page contents were read through a summarising fetch tool, not raw HTML, so re-read each cited page before relying on a number. Deadlines are AoE (UTC-12). Anything not stated on an official page is marked UNVERIFIED.

Work being placed (from the brief): a negative / exploratory empirical study. Normalised text diff beats RELIC on JCL-SemBench (180 pairs, MCC 0.525 vs 0.324) and on an 11-repo external run (F1 0.9978 vs 0.9755). RELIC's true positives are a strict subset of the text baseline's. The oracle is same-author and unvalidated, there is no held-out data, and human label validation is not complete.

## 1. Headline findings

1. **ResponsibleSE 2027 closes today (Fri 20 Nov 2026 AoE).** It is a workshop, not a conference track. The scope text is about "responsibility" in SE, not detector evaluation. The page does not mention negative results, artifacts, or a non-archival option. Submissions are archival in IEEE proceedings. Submitting a thin paper today could count as prior publication for a better venue later (see 3.1). I do not recommend it as the primary venue.
2. **Most negative-results tracks already closed.** SANER 2027 RENE closed 23 Oct 2026. MSR 2027 and ICST 2027 main paper deadlines passed. ReCode 2027 closed 13 Nov 2026.
3. **Open or upcoming with real fit:**
   - ICPC 2027 RENE: paper due 18 Dec 2026, but its scope is program comprehension.
   - ICSME 2027 Research track: paper due 26 Feb 2027. Negative results are not mentioned.
   - ICSME 2027 Registered Reports: dates "TO BE ANNOUNCED".
   - SANER 2028 RENE: no call yet found (UNVERIFIED).
4. **Biggest reviewer risk is construct validity, not the venue.** The old benchmark's label is about a non-cosmetic text edit, so a text-diff baseline beating RELIC is expected by construction. A RENE-style track penalises negative results that come from method or design flaws (see 3.2).

## 2. Venue table

| Venue | Type / negative results? | Pages | Deadline | Review | Verdict |
|---|---|---|---|---|---|
| ResponsibleSE 2027 (ICSE 2027 workshop, Dublin) | Workshop. Research 6-8, experience 6-8, short 4-6. Negative results not addressed. | 6-8 (research) | Paper **20 Nov 2026** (today); notification 11 Dec; camera-ready 29 Jan 2027 | Double-blind, IEEE template | Fit 2/5, maturity cost high. Not recommended. |
| ICPC 2027 RENE (Dublin) | Replications and negative/null results, explicitly in scope. | 10 + 2 refs (4+1 for negative results about previously published work) | Abstract 11 Dec 2026; paper 18 Dec 2026; notification 14 Jan 2027 | **Not** double-anonymous; anonymous reviewers, identities visible | Fit 2/5 on topic (program comprehension), 4/5 on format. Possible but topic risk. |
| ICSME 2027 Research (Toronto, 7-11 Sep 2027) | Full papers: maintenance/evolution, empirical studies. Negative results not mentioned. | 10 + 2 refs | Abstract 19 Feb 2027; paper 26 Feb 2027; early decisions 26 Apr | Double-blind. Title must differ from any arXiv preprint. | Fit 4/5 on topic. Needs the new validation evidence first. **Primary.** |
| ICSME 2027 Registered Reports | Confirmatory studies only get In-Principle Acceptance. Exploratory negative results welcome "if they offer deeper insight". | 6 + 1 refs, strict | TBA | Single-blind | Fits only a new pre-registered study (the held-out and human-review run), not the completed one. |
| ICSME 2027 Benchmark & Dataset track | Listed on the ICSME 2027 page. Its own page returned 404. | UNVERIFIED | UNVERIFIED | UNVERIFIED | Check once the page is live. JCL-SemBench might fit here. |
| SANER 2027 RENE | Negative results, 10 + 2 refs, double-anonymous | | Closed 23 Oct 2026 | | Missed. SANER 2028 call not found (UNVERIFIED). |
| SANER 2027 Registered Report | Initial report due 6 Nov 2026. Exploratory work gets Continuity Acceptance only. | 6 + 1 | Closed | Single-blind | Missed. |
| MSR 2027 Registered Reports | Initial report due 20 Nov 2026 (today). Exploratory allowed, negative results welcome. | 6 + 1 | Today | Anonymous reviewers | Not suitable. Needs a study not yet run, and an MSR-relevant mining angle. |
| MSR 2027 Data and Tool Showcase | Datasets and tools, not empirical studies | | Closed 10 Nov 2026 | | Missed. |
| ICST 2027 Research (San Sebastian, 17-21 May 2027) | Case, replication and empirical papers; "novel and original work". Negative results not mentioned. | 10 + 2 | Closed 2 Nov 2026 | Double-blind; anonymised replication package required | Missed. Tool papers and competition reports due 28 Feb 2027 are not relevant. |
| ReCode 2027 (ICSE 2027 workshop) | Legacy modernisation, code translation. Research papers 6 pages, benchmarks have no page limit. Non-archival option exists. | 6 | Closed 13 Nov 2026 | Double-anonymous | Best-fitting scope, but missed. Check AISM at ASE (2026 edition existed; no 2027 call found). |
| EMSE journal | Special issue RENE (deadline 20 Jun 2025) is closed. General author guidelines not retrieved. | | | | UNVERIFIED. Registered reports from ICSME/MSR/SANER are completed in EMSE. |
| arXiv + artifact | No gatekeeper. | | None | | Fallback. See section 4. |

## 3. Cross-cutting rules (official-source facts)

### 3.1 Originality and concurrent submission
- ICSME research: must not be "published, under review elsewhere, or submitted to another ICSME 2027 track".
- ICPC, MSR and SANER registered report pages: the same rule; the chairs may share submission lists and use plagiarism software.
- ResponsibleSE: only "original" is stated. No explicit policy.
- Consequence: an IEEE-archived workshop paper before a main-track submission risks overlap. The ResponsibleSE page does not offer a non-archival option. ReCode does.
- ICSME double-blind requires the title to differ from any arXiv preprint (checked on the ICSME 2027 research page). ICPC RENE is not double-anonymous, so preprint use is less of an issue there.

### 3.2 What the negative-results tracks say they reject
From the SANER 2027 RENE and ICPC 2027 RENE pages: criteria are depth and breadth of empirical study, clarity, appropriateness of conclusions, actionable insights, artifact availability and methodological rigor. "A negative result due primarily to misaligned expectations or low statistical power" is weak. The null result must reflect the phenomenon rather than flawed methods. The SANER and MSR registered-report pages say "we tried and failed" is not enough; the paper must explain why or what it implies.

### 3.3 Artifacts
- ICPC and SANER RENE: link all artifacts. Exception: proprietary data.
- ICST research: anonymised replication package, or explain why none.
- Formal Artifact Evaluation tracks exist at ICSE 2027 (registration 22 Jan, submission 29 Jan 2027) and ICSME 2027, but only for papers accepted there. Details UNVERIFIED.

### 3.4 Format
IEEE conference template everywhere checked. ICPC RENE: 10pt, PDF only, spacing deviations may desk-reject. Reference format beyond the IEEE template is not stated on any page (UNVERIFIED for IEEE numeric style).

### 3.5 AI disclosure
ICPC and MSR: generative AI cannot be an author, use must be disclosed. Relevant because RELIC's LLM baseline and any AI-assisted writing must be disclosed.

## 4. Recommendation

**Primary: ICSME 2027 (Research track, or Benchmark & Dataset if its call fits). Paper due 26 Feb 2027, abstract 19 Feb.** About 14 weeks remain. Use that time to produce what the work lacks:
1. A completed independent human review of the SemBench labels.
2. A frozen, pre-registered external run.
3. A reframe as "what this benchmark can and cannot measure" with the negative result as the finding, not as a tool paper. A pure negative-results paper is not an advertised category at ICSME 2027 (UNVERIFIED), so it would be judged as a full empirical paper.

Reasons: strongest topic fit (maintenance, legacy), a longer 10-page format, time to fix the validity gaps, and no loss of originality.

**Fallback: arXiv preprint plus archived artifact now (Zenodo or similar), then SANER 2028 RENE or ICPC 2027 RENE.**
- ICPC 2027 RENE is available on 18 Dec 2026 if the validity gaps cannot be closed in time. It is a fair home for a negative result, but the program comprehension scope is a stretch. Authors would have to argue that contract inference supports comprehension of batch jobs. Confirm scope with the track chairs first.
- A preprint publishes the negative finding with no gatekeeper, makes the artifact citable, and does not itself count as publication. Remember that ICSME requires a title that differs from the preprint.
- SANER 2028 RENE is likely in autumn 2027 by analogy (UNVERIFIED).

**Do not** submit to ResponsibleSE today. A rushed 6-page paper in IEEE proceedings could count as published work for ICSME. The scope does not mention evaluation methodology. The positioning document rests on ethics and responsibility framing that reviewers there will not mind, but it brings no extra credit at an SE evaluation venue.

## 5. What a reviewer would reject on
1. **The label is a text-edit predicate.** The old benchmark's label agreed with a text-edit predicate on 564/566. Text diff winning is therefore expected by construction, not evidence about RELIC.
2. **Same-author, unvalidated oracle** with no completed human review and no z/OS validation.
3. **No held-out data.** RELIC V2 was tuned on its evaluation files.
4. **Strict-subset result.** RELIC detects nothing the baseline misses. A reviewer will ask what RELIC adds, and why the paper is not simply "do not build this".
5. **Small, non-blind external sample** (roughly 4 to 11 repositories). RENE criteria penalise low power.
6. **Negative result from flawed methods.** See 3.2. It must be shown that the null is real.
7. **Licensing and provenance gaps** for external repositories, and LLM-baseline data sent to a third party.
8. **Overclaiming.** "Independent oracle", "first", or any superiority claim.

## 6. Recommended actions
1. Today: do nothing at ResponsibleSE unless the authors accept the originality risk. Tell the team the deadline is today.
2. This week: email the ICPC 2027 RENE chairs on scope, and decide go/no-go for 18 Dec 2026.
3. Now: post the preprint and artifact (with a title different from the planned submission).
4. By Jan 2027: finish the human label review, freeze RELIC V2 and the generator, and run the external pre-registered evaluation.
5. Check ICSME 2027 for the Benchmark & Dataset and Registered Reports pages when posted (dates and scope are TBA or 404 today).
6. Draft in IEEE two-column format, 10 + 2 pages, double-blind from the start.

## 7. Remaining uncertainty
- Whether ICSME 2027 accepts negative-results-only papers in the Research track (not stated).
- The ICSME 2027 Benchmark & Dataset and Registered Reports calls (404, TBA).
- ResponsibleSE: whether a workshop paper counts as prior publication for ICSME (no official statement found), and whether non-archival presentation is possible.
- ICPC RENE: whether JCL contract detection is accepted as in scope.
- The SANER 2028 RENE call and dates.
- EMSE journal guidelines, ESEM 2027, ASE 2027 and FSE 2027 workshop calls. These were not found or not fetched. Reference style beyond IEEE.
- All page contents came via a summarising fetch. Re-verify the numbers on the live pages.

## 8. Sources (all checked 2026-11-20)
- ResponsibleSE 2027: https://conf.researchr.org/home/icse-2027/responsiblese-2027
- ResponsibleSE series: https://conf.researchr.org/series/responsiblese
- ICSE 2027 dates: https://conf.researchr.org/dates/icse-2027
- ICPC 2027 RENE: https://conf.researchr.org/track/icpc-2027/icpc-2027-replications-and-negative-results--rene-
- ICSME 2027 home: https://conf.researchr.org/home/icsme-2027
- ICSME 2027 research: https://conf.researchr.org/track/icsme-2027/icsme-2027-papers
- ICSME 2027 dates: https://conf.researchr.org/dates/icsme-2027
- ICSME 2027 registered reports: https://conf.researchr.org/track/icsme-2027/icsme-2027-registered-reports
- SANER 2027 RENE: https://conf.researchr.org/track/saner-2027/saner-2027-reproducibility-studies-and-negative-results-rene-track
- SANER 2027 registered report: https://conf.researchr.org/track/saner-2027/saner-2027-registered-report-track
- SANER 2027 dates: https://conf.researchr.org/dates/saner-2027
- MSR 2027 registered reports: https://2027.msrconf.org/track/msr-2027-registered-reports
- ICST 2027 research: https://conf.researchr.org/track/icst-2027/icst-2027-research-papers
- ReCode 2027: https://conf.researchr.org/home/recode-2027
- EMSE RENE special issue (closed): https://emsejournal.github.io/special_issues/2024_SI_RENE.html (seen in search results only, not fetched)

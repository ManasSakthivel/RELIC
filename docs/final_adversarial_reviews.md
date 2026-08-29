# RELIC — Final Adversarial Review Report
<!-- Three-Panel Adversarial Review | Final Closure Sprint | 2026-08-30 -->

This document records the three independent adversarial reviews conducted as Phase 15 of the Final Closure Sprint.
Each reviewer attacks from a different angle. Findings are used to determine fix-or-document decisions in Phase 16.

---

## REVIEWER A — Software Engineering Reviewer (ICSE/FSE/ASE Standard)

### Strongest Strengths

1. **Self-documented attack surface:** Evidence ledger v3.0, frozen manifest, forensic audit trail, stale-value corrections, and split-key bug fix with commit hash citation. More rigorous infrastructure than most SE empirical papers.
2. **ALTER_ERROR_BRANCH is a genuine discriminating finding:** BCGDiff=1.0, Structural=0.0, Static-BCG=0.0 on 8 domain-clustered cases. Clear mechanism: confidence-delta catches threshold changes that structural graphs cannot see.
3. **Proactive limitation disclosure:** 91.8% simulation circularity, 0% real execution, FPR=0 as closed-set design, LLM lower bounds — all disclosed before being asked.

### Top 5 Rejection Risks

**Risk 1: Single Subject System — No External Validity** (Severity: REJECT at full research track)
- Evidence: All results from CardDemo. OOD F1=0.0 is oracle artifact, not generalization result. Second-system BLOCKED.
- Fixable: NO (requires unavailable external resources)
- Fix: Retarget to tool/short paper track, OR acquire second system before submission
- Blocks paper writing: YES (venue choice must be decided first)

**Risk 2: RQ1 Is Specification-Fidelity, Not Contract Recovery** (Severity: MAJOR_REVISION)
- Evidence: Evidence ledger own statement — "strongest valid claim: RELIC correctly implements TEMPORAL extraction per JCL spec." Oracle and SUT implement same deterministic rule. F1=1.0 guaranteed for any correct deterministic implementation.
- Fixable: YES (framing only) — rename RQ1 to "Contract Extraction Specification Compliance"
- Blocks paper writing: YES — RQ1 framing must be restructured

**Risk 3: Statistical Insufficiency** (Severity: MAJOR_REVISION)
- Evidence: RQ1 n=11 files, CI width=55pp. ALTER_ERROR_BRANCH n=8 domain-clustered. Three operators n=1 each.
- Fixable: YES (framing) — label correctly as ILLUSTRATIVE/DESCRIPTIVE; add power analysis footnote
- Blocks paper writing: NO if labeled correctly

**Risk 4: RQ3 Dynamic Validation Is Simulation Tautology** (Severity: MAJOR_REVISION)
- Evidence: 56/56 promotions from parser-generated simulations. Real execution rate=0%. Evidence ledger confirms circularity.
- Fixable: YES (framing only) — rename "JCL simulation corroboration rate"; remove "execution-grounded" from title
- Blocks paper writing: YES — title/abstract require revision

**Risk 5: LLM Baseline Comparison Is Uninformative** (Severity: MAJOR_REVISION)
- Evidence: 97-99% API failures. F1=0.038/0.109 are infrastructure lower bounds, not capability measurements.
- Fixable: YES — remove from main table; move to appendix as lower-bound investigation
- Blocks paper writing: YES — cannot claim RELIC outperforms LLMs with broken baseline

### Overall Assessment

**MAJOR REVISION — not ready for full research track submission.**
Core contribution (ALTER_ERROR_BRANCH detection via confidence-delta) is real and novel. Infrastructure is exemplary. Paper is blocked by single-system scope + three overreach points in RQ framing. Appropriate venues: ICSE/FSE tool track, ICSME NIER track, or workshop pending second-system acquisition.

---

## REVIEWER B — Systems/Legacy Modernization Reviewer

### Strongest Strengths

1. **Failure taxonomy is domain-correct and empirically grounded:** F1–F7 map to real mainframe modernization failure classes with documented sources. ALTER_ERROR_BRANCH (COND= threshold loosening) is the right problem.
2. **ALTER_ERROR_BRANCH result is the paper's most defensible finding:** Exactly the failure mode (COND= guard weakening) that structural tools cannot detect. Real domain insight, not a constructed artifact.
3. **Honest GnuCOBOL disclosure:** README states real-execution rate=0/61 directly. evidence_ledger RQ3-04 confirms. No attempt to hide the limitation.

### Top 5 Rejection Risks

**Risk 1: COND= Oracle Is Structurally Incomplete** (Severity: MAJOR_REVISION)
- Evidence: `jcl_parser.py` extracts COND= as raw string but does not semantically decode compound forms (COND=(rc,op,stepname), EVEN, ONLY). IF/THEN/ELSE/ENDIF (z/OS 1.9+) handled with `pass`.
- **NEW FINDING FROM AUDIT:** IF/THEN/ELSE/ENDIF: 0 files in CardDemo use this syntax. So current results are complete for CardDemo. PROC references: 3 files use `EXEC PROC=REPROC` (inline proc).
- Fixable: PARTIALLY — IF/ENDIF gap is real but does not affect CardDemo results. Must be disclosed in Threats to Validity.
- Blocks paper writing: NO (as long as disclosure is present)

**Risk 2: RQ3 Is Simulation Circularity** (Severity: MAJOR_REVISION)
- Evidence: Same as Reviewer A Risk 4. All 56 SUPPORTED from parser-generated traces.
- Fixable: YES (framing only)
- Blocks paper writing: YES

**Risk 3: PROC Reference Expansion Not Implemented** (Severity: MAJOR_REVISION for enterprise systems)
- Evidence: 3 CardDemo files use `EXEC PROC=REPROC`. Inline PROCs may not expand correctly.
- **NEW FINDING FROM AUDIT:** TRANREPT.jcl has 1 contract despite PROC reference → at least external step ordering works. 0 IF/ENDIF files confirms CardDemo uses older JCL syntax throughout.
- Fixable: PARTIALLY — does not affect CardDemo results; must be in Threats to Validity for generalization
- Blocks paper writing: NO (with proper disclosure)

**Risk 4: RQ1 Oracle/SUT Specification Sharing** (Severity: MAJOR_REVISION)
- Evidence: Same as Reviewer A Risk 2. Step-ordering spec is shared.
- Fixable: YES (framing only)
- Blocks paper writing: YES

**Risk 5: Single CardDemo Evaluation — No Enterprise JCL Coverage** (Severity: MAJOR_REVISION)
- Evidence: CardDemo is a demonstration application without GDG, VSAM KSDS/RRDS, RACF, CA7/TWS scheduling, catalogued PROCs. Real enterprise JCL has all of these.
- Fixable: NO (requires enterprise system access)
- Blocks paper writing: NO (with honest scope disclosure)

### Overall Assessment

**Major Revision Required. The core technical idea is sound; the evaluation packaging is overreaching in two places.**
Fixes needed: (1) Remove "execution-grounded" from title/abstract. (2) Reframe RQ3 as simulation consistency. Both are framing fixes requiring no new experiments. Static contribution stands independently.

---

## REVIEWER C — Stanford PhD Admissions / Research Maturity Reviewer

### Strongest Positive Signals

1. **Genuine epistemic discipline:** Evidence ledger key finding for RQ1 states: "The strongest valid claim is: RELIC correctly implements TEMPORAL contract extraction per the JCL step-ordering specification." A student who writes this about their own F1=1.0 result without being asked demonstrates exceptional self-awareness.
2. **Self-commissioned adversarial review:** Prior `final_hostile_review.md` (535 lines, 6 CRITICAL issues) was solicited before experiments ran and incorporated into the evidence ledger. This is not performative — the student found and fixed the reflexive-pair guard bug that *reduced* their mutation count from 109 to 104.
3. **Scientific integrity infrastructure in code:** 305 tests including SI-01 through SI-12 guards. NOT_OBSERVED ≠ CONTRADICTED enforcement. SYNTHETIC_STATIC contamination guard. Benchmark lock mechanism.

### Top 5 Red Flags

**Red Flag 1: RQ3 Title Claims "Execution-Grounded" But Execution is 0%** (Severity: DEAL_BREAKER for title)
- Specific evidence: RQ3-04 (VERIFIED): "real execution validation rate = 0%." evidence_ledger own statement: "near-guarantees promotion" via simulation circularity.
- Fixable: YES (framing only) — retitle; remove "execution-grounded" from abstract
- Required fix: Retitle. Replace "Execution-Grounded" in paper title with "Statically-Extracted" or similar.
- Blocks paper writing: YES

**Red Flag 2: RQ1 Oracle Shares Specification — F1=1.0 Is Vacuous** (Severity: SERIOUS_CONCERN)
- Specific evidence: RQ1-04 (VERIFIED): "ZERO shared code; both implement identical JCL grammar rule." evidence_ledger own statement: "For a deterministic algorithm implementing a deterministic spec, agreement=1.0 is expected."
- Fixable: YES (framing only) — lead with macro-F1=0.5455 CI[0.27,0.82]; relabel micro-F1 as spec-fidelity
- Required fix: Paper cannot headline micro-F1=1.0 as contract discovery result
- Blocks paper writing: YES

**Red Flag 3: N/A Rate 76.4% Without Sensitivity Prominently Reported** (Severity: SERIOUS_CONCERN)
- Specific evidence: F1=1.0 on 104/440 mutations. Sensitivity: worst-case F1=0.382. Evidence ledger has this but it must appear in paper's main table.
- Fixable: YES (paper writing) — add three-row F1 table (1.0, 0.500, 0.382)
- Required fix: All three F1 values in main results table
- Blocks paper writing: NO (fixable in writing)

**Red Flag 4: LLM Baselines Are Broken Infrastructure** (Severity: SERIOUS_CONCERN)
- Specific evidence: n_errors=245/248 (LLM-C). Groq 100K TPD quota exhausted after 3-7 calls.
- Fixable: YES — remove from main table; move to "preliminary lower-bound investigation" section
- Required fix: Do not compare RELIC to a baseline that never ran
- Blocks paper writing: PARTIALLY

**Red Flag 5: Headline Framing Still Overstates Evidence** (Severity: ADDRESSABLE)
- Specific evidence: README says "micro-F1=1.000" without immediate oracle-spec-sharing caveat. The honest version is in the evidence ledger but not in the README abstract.
- Fixable: YES — README/abstract need one paragraph re-scoping the contribution
- Blocks paper writing: NO (but must be fixed before submission)

### The Core Question

**The student understands rigorous methodology better than most but is still learning to lead with honest framing.**

The evidence ledger is publication-quality. The experimental infrastructure is exemplary. The self-corrections (split bug fix, reflexive-pair guard, BCGDiff engine fix) all went in the direction of making results *worse*, not better — exactly what scientific integrity requires.

The gap: the headline claims (README, FINAL_RESULTS.md headers) still present F1=1.0 and "91.8% dynamic validation" as primary results. The honest version — "spec-fidelity check" and "JCL simulation corroboration" — is buried in the evidence ledger. A Stanford committee needs to see those qualifications in the first paragraph, not the seventh.

**Verdict:** This is the work of a student who knows the truth and has documented it honestly — but is still learning that the headline must match the finding. The contribution is publishable at a workshop or tool track after framing fixes. The methodology is publishable at a full research venue after a second system is obtained. The infrastructure is already better than most published papers.

---

## Phase 16 Fix Gate Summary

| Issue | Fixable | Action |
|---|---|---|
| RQ3 "execution-grounded" framing | YES (paper writing) | Document in FINAL_SCIENTIFIC_STATUS.md — fix during paper writing |
| RQ1 F1=1.0 framing | YES (paper writing) | Document — fix during paper writing |
| N/A sensitivity in results table | YES (paper writing) | Document — fix during paper writing |
| LLM baselines in main table | YES (paper writing) | Document — fix during paper writing |
| Worst-case F1 rounding (0.384→0.382) | YES (NOW) | FIXED in evidence_ledger.md v4.0 |
| McNemar test documentation | YES (NOW) | FIXED in evidence_ledger.md v4.0 |
| PROC expansion disclosure | YES (NOW) | FIXED in final_failure_analysis.md (F-08) |
| Second system search documentation | YES (NOW) | FIXED — secondary_system_candidates.json + secondary_system_selection.md |
| IF/ENDIF coverage measurement | YES (NOW) | FIXED — 0 files in CardDemo, documented in failure analysis F-08 |
| Single system scope disclosure | DOCUMENT | Cannot be fixed without external resources |
| Level-3 human annotation | DOCUMENT | Blocked — external human dependency |
| LLM baseline re-run | DOCUMENT | Blocked — requires paid API tier |
| z/OS execution | DOCUMENT | Blocked — no z/OS environment available |

---

*Generated: RELIC Final Closure Sprint | Three-Panel Adversarial Review | 2026-08-30*

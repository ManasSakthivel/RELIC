# RELIC V2 — Remaining technical risks

Ordered by impact on the validity of what can be claimed.

## Validity risks (cannot be closed by code)

1. **No held-out evaluation.** All three corpora were inspected while diagnosing
   and choosing fixes. V2's F1 0.980 (v1.1 0.951) is a development result and
   probably optimistic. Needed: a corpus never opened during development,
   frozen detector, pre-registered metric. *External validation pending.*
2. **No independent oracle validation.** Oracle, mutator and detector have one
   author; mutator and oracle share a lexer; no comparison with real z/OS
   execution or an independent mainframe reviewer (D-013).
3. **Benchmark cannot separate RELIC from a trivial rule.** Negatives are 98 %
   comment/MSGCLASS edits; a normalised text diff scores F1 0.998 (D-014). Needed:
   benign reorder/split/rename/symbol-change negatives and realistic (e.g.
   mined change-history) mutations.
4. **LLM comparison unfair/incomplete.** 183 invalid outputs with positive-class
   selection bias; model/provider documented inconsistently; no credentialed
   re-run (D-016, D-017).
5. **Fix selection on the evaluation data.** D-001…D-004 were found in the same
   files used to score them. The ablation and bootstrap quantify sampling noise,
   not this selection effect.
6. **Production JCL compatibility is not claimed** and not evidenced: the corpus
   is three open-source projects, 66 evaluable files.

## Functional risks (documented, not fixed)

| Risk | Reference |
|---|---|
| PROC/INCLUDE/IF-THEN-ELSE unsupported; PROC-internal DD overrides missed | D-006 |
| Same-named step swaps invisible to name-based identity | D-005 |
| D-004 drops detection of renames of pre-deleted datasets (no "deletes" contract) | D-004 |
| RESOURCE truth includes program I/O that JCL cannot show; OMP recovery 0/23 | D-007 |
| No cross-file RESOURCE contracts | D-008 |
| COND strengthening and `EVEN/ONLY` unmodelled | D-009, D-010 |
| Symbolic DSNs (`&SYM`), `&&TEMP` scoping, unnamed concatenations | D-011 |
| Unverified default when DSN present but DISP absent | D-012 |
| `NAME#n` identity shifts when a same-named step is inserted earlier | D-001 scope |

## Process risks

* V2 fixes are opt-in and **not** in `all_detectors()`; `results/final` and the
  paper's numbers still describe v1.0.0/v1.1. Anyone citing "V2" must cite
  `results/v2` and the development-only status.
* README/paper/limitations text contains the inaccurate statements listed in
  D-014, D-015, D-016, D-017, D-018, D-019. They belong to the research lead's
  manuscript scope and were left untouched; this register is the hand-off.
* `v2_run_info.json` is non-deterministic (timestamp) by design.
* The default `legacy_v1_0` code path was edited (refactor to add flags). It is
  covered by the unchanged 391 original tests and by a full-pipeline
  reproduction that left every tracked `results/` file identical (see
  `EVALUATION_SUMMARY.md` §6).

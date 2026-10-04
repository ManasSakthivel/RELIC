# Threats to Validity

Detailed entries with evidence and next steps: [limitations.md](limitations.md).

## Construct validity
- *Ground truth = simulated JCL semantics.* The label "behaviour changed" is
  defined by the oracle's observables (execution, dataflow, final catalog,
  termination) under return-code and abend scenarios. A different definition
  (e.g. normal completion only) changes the results; the `no_abend` sensitivity
  analysis reports this (L3, L4).
- *Prediction = any risk item.* RELIC is scored as flagging when it reports any
  broken or weakened contract, including items it marks as false-positive
  candidates (the same rule as the legacy harness). Its explanations, which are
  its intended output, are not evaluated.
- *Synthetic faults* stand in for migration defects (L6).

## Internal validity
- *Oracle–system dependence.* The oracle shares no code with RELIC and never
  sees the mutation, but both were read against the same JCL reference. A
  shared blind spot was found and fixed; others may remain (L3).
- *Post-hoc fixes.* Only RELIC v1.0.0 is a blind result (L8).
- *Generator–oracle coupling.* The mutation generator uses the oracle's lexer to
  locate sites. This affects which mutants exist, not their labels.
- *Scope rules* (IF/THEN/ELSE, cross-file renames) were declared from RELIC's
  documented scope before results were computed. Results including the
  out-of-scope mutants are reported.

## External validity
- Three demonstration/teaching corpora; CardDemo dominates; single-file analysis
  (L1, L2, L5). No claim is made about production systems or other languages.
- Multi-subject evaluation by the RELIC authors, not third-party external
  validation (L13). Only TEMPORAL, RESOURCE and CONTROL_FLOW contracts (L14).
- The LLM comparison covers one model and one prompt (L10).

## Conclusion validity
- Mutants within a file are correlated. File-level cluster bootstrap intervals
  are reported, and Wilson intervals are labelled as ignoring clustering. No
  significance tests are reported: the clustering and small secondary samples
  would make their assumptions doubtful (L12).

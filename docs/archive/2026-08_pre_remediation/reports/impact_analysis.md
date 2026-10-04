# Impact Analysis Report

**Date:** 2025

---

## ImpactRadius Functionality

The `RiskDetector.compute_impact_radius()` method computes structural impact around a broken contract using entity-sharing analysis.

**Algorithm:**
1. Seed entities = {subject_id, object_id} of broken contract
2. Direct contracts: any other contract sharing a seed entity
3. Transitive contracts: contracts sharing an entity with any direct contract (depth-1 expansion)
4. Returns ImpactRadius with direct and transitive counts

**Key caveat (built into method):**
> "Impact radius is a structural upper bound. Semantic impact requires execution evidence or human validation."

---

## Evaluated in RQ2

For the 10 SUPPRESS_RETURN_CODE_CHECK detections, the impact radius was not explicitly computed in the RQ2 run. The ImpactRadius is available through the API but was not integrated into the automated results. A future run should call `compute_impact_radius()` for each detected risk and include it in the risk report.

---

## Structural vs Semantic Impact Distinction

This distinction is critical and must be maintained in the paper:

| Type | Method | Guarantee |
|------|--------|-----------|
| Structural impact | Entity-sharing graph traversal | Upper bound only |
| Semantic impact | Execution trace evidence + human annotation | Lower bound from observation |

A contract that is structurally impacted may not be semantically affected if the entities are weakly coupled. A contract that is NOT structurally impacted could still be semantically affected through non-captured dependencies (VSAM, JES2 spool, etc.).

---

## Recommendation

The paper should present ImpactRadius as a "structural risk scoping" tool, not as a semantic impact claim. The explanation chain in RiskItem already carries this distinction through the `AFFECTED ARTIFACTS` step which states artifact IDs, not semantic consequences.

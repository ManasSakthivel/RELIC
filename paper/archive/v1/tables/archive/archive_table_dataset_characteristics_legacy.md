# Table 2: Dataset Characteristics

## Primary Dataset: AWS CardDemo

| Property | Value |
|----------|-------|
| **Source** | GitHub: `aws-samples/aws-mainframe-modernization-carddemo` |
| **License** | Apache License 2.0 |
| **Version** | Commit `main`, 2024-Q4 snapshot |
| **COBOL Programs** | ~30 |
| **JCL Files** | ~15 |
| **Copybooks** | ~20 |
| **Estimated LOC** | ~15,000 (COBOL + JCL + copybooks) |
| **Executable** | Yes — GnuCOBOL 3.1.2 on Linux/macOS |
| **Dynamic Evidence Available** | Yes (via GnuCOBOL instrumentation) |
| **Dataset Split** | Development (70%) / Validation (30%) |
| **Limitations** | Smaller than enterprise systems; designed as demonstration |
| **Modification Status** | Not modified; used as-is |

### CardDemo Notable Properties

- Represents a realistic credit card transaction processing system
- Contains batch jobs (COBOL programs invoked from JCL) and online transactions
- VSAM cluster initialization is documented in the repo (motivates F2 mutations)
- COND parameter usage in JCL provides control-flow contracts (F3 mutations)
- Job ordering between CBACT04C and CBTRN02C documented in issue tracker (F1 mutations)
- GnuCOBOL-compilable; execution traces can be collected reproducibly

---

## Held-Out Dataset: Open Mainframe Project (OMP) Public COBOL

| Property | Value |
|----------|-------|
| **Source** | GitHub: `openmainframeproject/` repositories |
| **License** | Apache License 2.0 |
| **Version** | Snapshot 2024-Q4 |
| **COBOL Programs** | ~50 |
| **JCL Files** | 0 (COBOL-only; no JCL provided) |
| **Copybooks** | ~10 |
| **Estimated LOC** | ~20,000 |
| **Executable** | Partial (some programs require external data) |
| **Dynamic Evidence Available** | Limited |
| **Dataset Split** | Held-out (not examined during development) |
| **Limitations** | No JCL; mostly isolated programs; limited cross-artifact contracts |
| **Modification Status** | Not modified; used as-is |

---

## Dataset Usage Policy

1. **No proprietary data**: Neither IBM proprietary source code nor IBM customer data is used.
2. **No AD-Scan data**: No IBM internal benchmark or scanning data is used.
3. **License compliance**: All datasets used under their documented open-source licenses.
4. **No data leakage**: Held-out dataset systems not examined during development, threshold selection, or prompt engineering.
5. **Reproducibility**: All datasets are publicly available; download instructions in `docs/dataset_selection.md`.
6. **Trace labeling**: All GnuCOBOL execution traces labeled `EXECUTION (GnuCOBOL environment, NOT z/OS)`. Synthetic traces labeled `SYNTHETIC_STATIC`.

---

## Evidence Collection Protocol

| Evidence Type | Source | Label in System |
|--------------|--------|----------------|
| Real execution (COBOL programs) | GnuCOBOL 3.1.2 | `EXECUTION` |
| JCL step simulation | Batch simulator | `EXECUTION_SIMULATED` |
| Statically-derived traces | Static analysis | `SYNTHETIC_STATIC` |
| Human trace reconstruction | Annotation | `HUMAN` |

**Scientific integrity:** `EXECUTION` and `SYNTHETIC_STATIC` evidence must never be combined without explicit labeling. Confidence vectors distinguish evidence source type.

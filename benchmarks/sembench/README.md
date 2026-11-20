# JCL-SemBench: Execution-Semantics Benchmark for JCL Equivalence & Regression Detection

`JCL-SemBench` is a benchmark of 180 matched `(original, transformed)` z/OS JCL pairs designed to rigorously evaluate semantic equivalence detectors, contract recovery tools, and refactoring safety checkers.

Unlike syntactic mutation benchmarks whose negative (preserving) pairs are dominated by trivial comment or whitespace edits, `JCL-SemBench` includes non-trivial, structural, and subtle edge cases across 12 balanced semantic categories grounded in the **IBM z/OS MVS JCL Reference**.

---

## 1. Directory Structure

```
benchmarks/sembench/
├── cases.jsonl             # Main JSONL dataset (1 record per pair)
├── cases/                  # Subdirectory containing paired JCL files
│   ├── sembench_001/
│   │   ├── original.jcl
│   │   └── transformed.jcl
│   └── ...
├── MANIFEST.sha256         # Frozen SHA-256 manifest of all original/transformed files
├── oracle_validation.json  # Machine-readable validation and category breakdown
├── build.py                # Deterministic benchmark generator script
├── validate.py             # Standalone verification script (checks SHA-256 and oracle)
└── README.md               # This documentation
```

---

## 2. Record Schema (`cases.jsonl`)

Each line in `cases.jsonl` is a JSON object with the following fields:

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Unique case identifier (e.g. `sembench_001`). |
| `base_id` | `string` | Identifier of the underlying base job (e.g. `base_hw_01_etl`, `corpus_carddemo_cbpaup0j`). |
| `source` | `string` | Origin of base job (`handwritten` or `corpus:<relative_path>`). |
| `category` | `string` | High-level semantic category (12 categories, 6 preserving, 6 changing). |
| `subcategory` | `string` | Specific transformation rule tested. |
| `expected_outcome` | `string` | Ground truth label: `PRESERVING` or `CHANGING`. |
| `original_sha256` | `string` | SHA-256 checksum of `original.jcl`. |
| `transformed_sha256` | `string` | SHA-256 checksum of `transformed.jcl`. |
| `relevant_jcl_semantics` | `string` | Citation to the IBM z/OS MVS JCL Reference section or concept. |
| `rationale` | `string` | Why this case was constructed and what pattern it tests. |
| `equivalence_argument` | `string` | Explicit justification of equivalence or behavioral divergence under JCL semantics. |
| `oracle_verdict` | `object` | Detailed output from `jcl_oracle.judge.compare_versions`. |
| `oracle_agrees_with_expected` | `boolean` | Whether the oracle verdict matches the expected ground-truth outcome. |
| `oracle_confidence` | `string` | `HIGH`, `MEDIUM`, or `LOW`. |
| `independent_review_status` | `string` | Always `PENDING` (no external reviewer claim). |
| `validation_status` | `string` | `VALIDATED_BY_ORACLE_AND_ARGUMENT`, `ORACLE_DISAGREES`, `ORACLE_ABSTAINS`, or `ARGUMENT_ONLY`. |

---

## 3. Taxonomy of Categories

### Behaviour-Preserving (87 Pairs)
1. **`comment_edit`** (17 pairs): Insertion, deletion, inline comments, and banner/trailer comments.
2. **`whitespace_and_continuation`** (17 pairs): Columns 4–16 indentation, line splitting, line joining, blank-line handling.
3. **`syntax_representation`** (21 pairs): `DSN` vs `DSNAME`, `DISP=SHR` vs `DISP=(SHR)`, keyword order in DD/EXEC, COND parentheses, PARM formatting.
4. **`job_card_refactor`** (12 pairs): `MSGCLASS`, `CLASS`, `NOTIFY`, accounting information.
5. **`independent_statement_reorder`** (14 pairs): Independent DD statement reordering within utility/sort/compile steps.
6. **`unreferenced_step_rename`** (6 pairs): Systematic rename of unreferenced steps and internal references.

### Behaviour-Changing (93 Pairs)
7. **`step_reorder_dependent`** (14 pairs): Swapping producer/consumer steps, compile/link steps, abend boundary alterations.
8. **`dataset_dependency_change`** (17 pairs): Broken dataset links, GDG generation swaps, input feed redirects.
9. **`disp_change`** (19 pairs): `NEW` $\to$ `OLD`, `CATLG` $\to$ `DELETE`, abnormal disposition modifications, `SHR` $\to$ `OLD` concurrency lockouts.
10. **`cond_logic_change`** (18 pairs): Relational operator inversion (`LT` $\to$ `GE`), threshold shifts (RC 4 $\to$ 8), `COND=EVEN` removals.
11. **`producer_consumer_change`** (12 pairs): Step deletions, work DD deletions, pipeline truncations.
12. **`return_code_effect`** (13 pairs): IDCAMS delete/define alterations, DFSORT key inversion, record length conflicts.

---

## 4. How to Rebuild and Validate

### Rebuilding the Benchmark
To deterministically regenerate all pairs, case files, manifests, and validation summaries:
```bash
PYTHONPATH=$PWD/src:$PWD .venv/bin/python benchmarks/sembench/build.py
```

### Validating the Benchmark
To verify SHA-256 file hashes against `MANIFEST.sha256` and re-run `jcl_oracle` simulation on every case:
```bash
PYTHONPATH=$PWD/src:$PWD .venv/bin/python benchmarks/sembench/validate.py
```

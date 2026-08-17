# Dataset Final Report

## Summary
Two public datasets were attempted using the existing downloader in [`download.py`](src/legacy_contract/datasets/download.py:251). Both downloads succeeded on 2026-08-14, inventories were generated, and deterministic 60/20/20 splits were materialized without mixing dev, validation, and held-out artifacts.

## What was attempted
1. CardDemo download via `PYTHONPATH=src python3 -m legacy_contract.datasets.download carddemo`
2. OMP COBOL download via `PYTHONPATH=src python3 -m legacy_contract.datasets.download public_cobol`
3. File inventory checks under [`datasets/`](datasets/), [`traces/`](traces/), and [`benchmark/`](benchmark/)
4. Creation of [`results/dataset_manifest.json`](results/dataset_manifest.json)
5. Creation of this report at [`docs/dataset_final_report.md`](docs/dataset_final_report.md)

## Download results
### CardDemo
- Status: SUCCESS
- Source: <https://github.com/aws-samples/aws-mainframe-modernization-carddemo>
- License: Apache 2.0
- Downloader output summary:
  - Downloaded archive: `datasets/carddemo/aws-mainframe-modernization-carddemo-main.zip`
  - Archive size: 4.00 MB
  - Extracted successfully
  - Legacy artifacts found: 161
  - Artifact types: 44 COBOL, 62 COPYBOOK, 55 JCL
- Download error: none

### Public COBOL
- Status: SUCCESS
- Source: <https://github.com/openmainframeproject/cobol-programming-course>
- License: Apache 2.0
- Downloader output summary:
  - Downloaded archive: `datasets/public_cobol/cobol-programming-course-master.zip`
  - Archive size: 32.23 MB
  - Extracted successfully
  - Legacy artifacts found: 50
  - Artifact types: 7 COBOL, 0 COPYBOOK, 43 JCL
- Download error: none

## Actual artifact inventory
### CardDemo inventory
- Manifest: [`datasets/carddemo/ARTIFACTS.json`](datasets/carddemo/ARTIFACTS.json)
- Provenance: [`datasets/carddemo/DATASET_VERSION.txt`](datasets/carddemo/DATASET_VERSION.txt)
- Split file: [`datasets/carddemo/SPLITS_60_20_20.json`](datasets/carddemo/SPLITS_60_20_20.json)
- Artifact count: 161
- Total artifact bytes: 2,459,686
- Size range: 406 to 182,463 bytes
- Type counts:
  - JCL: 55
  - COBOL: 44
  - COPYBOOK: 62
- Example artifacts with SHA-256 and size:
  - `app/app-authorization-ims-db2-mq/cbl/CBPAUP0C.cbl` — COBOL — 14,832 bytes — `309468a5c4745f92c6dcf6ed28b396334b2f131ced78eb43eda962a63d2b174e`
  - `app/app-authorization-ims-db2-mq/cpy/CCPAUERY.cpy` — COPYBOOK — 2,779 bytes — `df7164d2732832f109a8efa71055931174c58af6889a17e59a4b2aa85ce62f03`
  - `app/app-authorization-ims-db2-mq/jcl/CBPAUP0J.jcl` — JCL — 1,732 bytes — `99e84914708d330fd3b8d19ce8b731ed5acd9b4e0dbdc16af8823802a01b68e4`
- Full per-file hashes and sizes are recorded in [`datasets/carddemo/ARTIFACTS.json`](datasets/carddemo/ARTIFACTS.json) and mirrored into [`results/dataset_manifest.json`](results/dataset_manifest.json).

### Public COBOL inventory
- Manifest: [`datasets/public_cobol/ARTIFACTS.json`](datasets/public_cobol/ARTIFACTS.json)
- Provenance: [`datasets/public_cobol/DATASET_VERSION.txt`](datasets/public_cobol/DATASET_VERSION.txt)
- Split file: [`datasets/public_cobol/SPLITS_60_20_20.json`](datasets/public_cobol/SPLITS_60_20_20.json)
- Artifact count: 50
- Total artifact bytes: 93,086
- Size range: 276 to 12,982 bytes
- Type counts:
  - JCL: 43
  - COBOL: 7
  - COPYBOOK: 0
- Example artifacts with SHA-256 and size:
  - `COBOL Programming Course #2 - Learning COBOL/Labs/jcl/ADDAMT.jcl` — JCL — 763 bytes — `22225a047b6e43f516f0d4391cd89244fa2f3ff417836031aee062a0b9288a42`
  - `COBOL Programming Course #3 - Advanced Topics/Challenges/Debugging/cbl/CBL0106.cbl` — COBOL — 7,147 bytes — `3cde3ac691111fcb8e9f00d4bc537ca48dc0a860d04fd075f73071547a4be67a`
  - `COBOL Programming Course #4 - Testing/Labs/jcl/EMPPAY.JCL` — JCL — 791 bytes — `5272216a78eec24f88e15636ea206efbf1607125c45e56687e4ea4a94c9d277b`
- Full per-file hashes and sizes are recorded in [`datasets/public_cobol/ARTIFACTS.json`](datasets/public_cobol/ARTIFACTS.json) and mirrored into [`results/dataset_manifest.json`](results/dataset_manifest.json).

## Split strategy and rationale
- Required policy: seed=42, 60/20/20 dev/validation/held_out.
- The existing [`create_split()`](src/legacy_contract/datasets/download.py:437) implementation is stratified by artifact type and deterministic for a fixed seed.
- To satisfy the required 60/20/20 ratio, split files were materialized separately from the CLI defaults:
  - CardDemo split counts: 96 dev, 32 validation, 33 held_out
  - Public COBOL split counts: 30 dev, 10 validation, 10 held_out
- Split files:
  - [`datasets/carddemo/SPLITS_60_20_20.json`](datasets/carddemo/SPLITS_60_20_20.json)
  - [`datasets/public_cobol/SPLITS_60_20_20.json`](datasets/public_cobol/SPLITS_60_20_20.json)
- Held-out data must not influence thresholding or tuning decisions.

## Exclusion criteria
- Included only files recognized by legacy extensions in [`_LEGACY_EXTENSIONS`](src/legacy_contract/datasets/download.py:57): `.jcl`, `.cbl`, `.cob`, `.cpy`, `.copy` and case variants.
- Excluded non-legacy files such as images, markdown, shell scripts, binaries, diagrams, archives inside extracted repos, assembler, control files, DDL, DCL, PSB/DBD, and other unsupported formats.
- No additional fabricated or placeholder entries were created.
- No parse-error-based exclusions were applied at this stage because parsing/compilation was not executed in this task.

## Existing files outside datasets
### traces/
- No files found under [`traces/`](traces/).

### benchmark/
- Found one file: [`benchmark/ground_truth/level2_deterministic.json`](benchmark/ground_truth/level2_deterministic.json)

## GnuCOBOL equivalence limitations
- GnuCOBOL-based execution is not semantically equivalent to full z/OS behavior for all artifacts.
- VSAM-dependent behavior is not fully supported.
- z/OS-specific ABEND codes and operational failure semantics are excluded from direct equivalence claims.
- JCL scheduling, JES behavior, DB2, IMS, CICS, MQ, and RACF/environment-specific semantics may require mocking or static-only treatment.

## What experiments can run
- Static artifact inventory and checksum-based reproducibility checks can run using [`results/dataset_manifest.json`](results/dataset_manifest.json).
- Static analyses over COBOL/JCL/copybook corpora can run on the dev and validation splits for both datasets.
- Held-out evaluation can run later because held-out lists are explicitly separated.
- Benchmark comparisons against [`benchmark/ground_truth/level2_deterministic.json`](benchmark/ground_truth/level2_deterministic.json) may proceed only for tasks that do not require dynamic traces.

## What experiments cannot run
- RQ3-style experiments requiring execution traces cannot currently run because [`traces/`](traces/) is empty.
- Any experiment requiring full z/OS subsystem fidelity for IMS, DB2, MQ, CICS, VSAM runtime behavior, or ABEND-faithful execution cannot be claimed from the currently downloaded source artifacts alone.
- Any tuning procedure must avoid held-out artifacts; if current pipelines do not enforce that separation, those experiments are blocked until enforcement is verified.

## Blocking status
- CardDemo dataset: available; experiments depending only on downloaded source artifacts are not blocked.
- Public COBOL dataset: available; experiments depending only on downloaded source artifacts are not blocked.
- Trace-dependent experiments: BLOCKED pending trace generation. RQ results remain [RESULT_PENDING].

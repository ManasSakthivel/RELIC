# CardDemo Dataset

**AWS Mainframe Modernization CardDemo — Research Evaluation Corpus**

---

## Source

| Field | Value |
|---|---|
| Name | AWS Mainframe Modernization CardDemo |
| Source URL | https://github.com/aws-samples/aws-mainframe-modernization-carddemo |
| License | Apache License 2.0 |
| Copyright | Amazon.com, Inc. or its affiliates |
| Version | `main` branch (downloaded 2026-08-14) |
| Download timestamp | 2026-08-14T16:44:53Z |

The full license text is at:
`datasets/carddemo/extracted/aws-mainframe-modernization-carddemo-main/LICENSE`

Attribution notice:
`datasets/carddemo/extracted/aws-mainframe-modernization-carddemo-main/NOTICE`

---

## Artifact Counts

| Type | Count | Notes |
|---|---|---|
| Total artifacts | 161 | Per `ARTIFACTS.json` |
| JCL files | 55 | Job Control Language (`.jcl`) |
| COBOL programs | 44 | COBOL source (`.cbl`) |
| Copybooks | 62 | COBOL copybooks (`.cpy`) |

Parser coverage: JCL 55/55 (100%), COBOL 44/44 (100%).

---

## Dataset Split

Split methodology: 60/20/20 (dev / validation / test), stratified by artifact type,
random seed = 42.

Split file: `datasets/carddemo/SPLITS_60_20_20.json`

This split is **frozen**. Do not alter it — changing the split would invalidate
comparison with reported results.

---

## Artifact Manifest

`datasets/carddemo/ARTIFACTS.json` — SHA-256 checksums and sizes for all 161 artifacts.

Used by `make download-carddemo` to verify integrity after download.

---

## Dataset Contents

CardDemo is a realistic but simplified mainframe credit-card processing application.
It includes:

- JCL job streams for batch transaction processing, reporting, and data management
- COBOL programs implementing business logic (account, card, transaction processing)
- Copybooks defining shared data structures
- BMS maps, DDL, DCL, IMS definitions (not used in this evaluation)

The evaluation in this research uses only JCL, COBOL, and copybook artifacts.
Other artifact types (BMS, DDL, ASM) are present in the extracted directory but
not parsed or analyzed.

---

## Redistribution

CardDemo is distributed under Apache License 2.0, which permits redistribution
with attribution and license preservation. The `LICENSE` and `NOTICE` files from
the original repository are preserved in the extracted directory.

This repository includes the full CardDemo source in `datasets/carddemo/extracted/`
to support reproducibility without requiring a network connection at experiment time.

---

## Limitations

- CardDemo is a **demonstration application**, not a production enterprise system.
  Real enterprise mainframe systems may have thousands of JCL jobs and COBOL programs.
- Results on CardDemo should not be extrapolated to arbitrary enterprise systems.
- The application was designed to showcase mainframe modernization scenarios;
  it may be more amenable to automated analysis than production legacy code.

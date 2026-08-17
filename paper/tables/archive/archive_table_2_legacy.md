# Table 2: Dataset Characteristics

| Dataset | Source | License | JCL Files | COBOL Programs | Copybooks | Total Artifacts | Executable | Splits |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| CardDemo | AWS GitHub | Apache 2.0 | 55 | 44 | 62 | 161 | No (DB2/CICS required) | dev/val/held-out = 60/20/20, seed=42 |
| OMP/public_cobol | GitHub IBM | Apache 2.0 | 43 | 7 | 0 | 50 | Partial (GnuCOBOL) | dev/val/held-out = 60/20/20, seed=42 |

*Note: Total artifacts for CardDemo: 55 JCL + 44 COBOL + 62 COPYBOOK = 161. Total artifacts for OMP/public_cobol: 43 JCL + 7 COBOL = 50.*

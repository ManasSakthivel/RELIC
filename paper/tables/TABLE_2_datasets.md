# Table 2 — Dataset Characteristics

| Dataset | Source | License | JCL Files | COBOL Files | Copybooks | Total | Executable |
|---|---|---|---|---|---|---|---|
| AWS CardDemo | AWS GitHub | Apache 2.0 | 55 | 44 | 62 | 161 | No (DB2/CICS/IMS required) |
| OMP Public COBOL | GitHub (IBM) | Apache 2.0 | 43 | 7 | 0 | 50 | Partial (GnuCOBOL 3.2.0) |
| **Total** | | | **98** | **51** | **62** | **211** | |

**Splits (seed=42):** dev=60%, validation=20%, held-out=20%

| Dataset | Dev | Val | Held-out |
|---|---|---|---|
| CardDemo | 96 | 32 | 33 |
| OMP Public COBOL | 30 | 10 | 10 |

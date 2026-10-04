# Table 9 — Computational Cost

All measurements on Apple M-series CPU, Python 3.11.15, macOS arm64.

| Phase | Input | Approx. Time | Memory | Notes |
|---|---|---|---|---|
| JCL parsing (all files) | 98 JCL files | < 1s | < 50 MB | JCLParser deterministic |
| Static contract extraction | 98 BCGs | < 1s | < 50 MB | StaticContractExtractor deterministic |
| BCG construction | 98 BCGs | < 1s | < 50 MB | BCGBuilder in-memory |
| Mutation benchmark (RQ2) | 440 mutations × 2 methods | < 2s | < 100 MB | All in-memory, no disk I/O |
| GnuCOBOL compile (EMPPAY) | 1 COBOL file | < 2s | N/A | cobc 3.2.0, -x flag |
| GnuCOBOL compile (DEPTPAY) | 1 COBOL file | < 2s | N/A | cobc 3.2.0, -x flag |
| JCL ordering trace generation | 20 JCL files | < 1s | < 20 MB | Parser-derived, not real execution |
| RQ1 bootstrap CI (10,000 iter) | 139 GT items | < 1s | < 10 MB | NumPy/random sampling |
| Full test suite (265 tests) | All modules | 0.14s | < 100 MB | pytest, no mocks |

**Total end-to-end pipeline (excluding LLM calls):** < 10 seconds on commodity hardware.

LLM conditions (Baseline C, D, E7) are not measured here as they require API access. Token cost would depend on model choice and prompt length (typically ~500–1000 tokens per mutation item).

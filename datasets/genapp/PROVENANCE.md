# GenApp subject — provenance

* Source: https://github.com/cicsdev/cics-genapp
* Commit: `f6f3f4b2580d31b7d8dcc31ce3e3676f4cceaaaa` (2026-07-10), retrieved 2026-10-04
* License: Eclipse Public License 2.0 — full text in `source/LICENSE`; copyright IBM Corp.
* Files vendored, unmodified: `base/cntl/*.jcl` (30 files, 29 contain a JOB statement),
  `base/cntl/README.md`, `base/src/*.cbl`, `base/src/*.cpy`, `README.md`, `LICENSE`.
* Use: secondary subject system for the source-level mutation benchmark.
  The JCL is installation/build JCL (COBOL compile and link via an in-stream
  procedure, DB2 DDL through TSO batch, CICS/VSAM definitions) containing
  `<PLACEHOLDER>` tokens that the original installation process substitutes.
  These tokens are treated as literal text by RELIC and by the oracle alike.
* Why chosen: independently authored (IBM, not AWS), permissively licensed, multi-step
  JCL with COND guards and dataset dependencies. Rejected alternative: Rocket/Micro Focus
  BankDemo (license limits use to demonstrations with Rocket products).

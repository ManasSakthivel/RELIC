# Contributing to RELIC

Thank you for your interest in this research project.

## Research Integrity First

RELIC is an academic research artifact. The primary obligation is
**scientific reproducibility and honesty**. Before contributing, read:

- `docs/methodology.md` — research design and frozen experimental scope
- `docs/limitations.md` — known limitations that must not be hidden
- `results/FINAL_RESULTS_MANIFEST.json` — frozen result values

**Do not alter the frozen experimental results.** If you find a bug that
affects a reported result, open an issue and document it clearly before
fixing anything.

## How to Contribute

### Reporting Bugs

Open a GitHub issue with:
1. A minimal reproducible example
2. Expected vs actual behavior
3. Python version, OS, GnuCOBOL version
4. Whether the bug affects any reported experimental result

### Suggesting Extensions

RELIC is designed to be extended. High-value extensions include:

- Additional mutation operators (F4–F7 categories)
- Level-3 human annotation of RESOURCE and CONTROL_FLOW contracts
- Additional JCL/COBOL corpora for generalization evaluation
- Data and state contract types (Paper 2 scope)
- z/OS execution trace adapters

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-description`
3. Write tests — all new features need tests in `tests/`
4. Run `make test` and ensure all 305+ tests pass
5. Run `make lint` — black, ruff, mypy must all pass
6. Submit a pull request with a clear description

### Code Standards

- Python 3.11+, formatted with `black` (line length 100)
- Type annotations required on all public functions
- Docstrings required on all public classes and methods
- No absolute paths; use `pathlib.Path` relative to project root
- No secrets or API keys in any file

## Running Tests

```bash
make setup          # install dependencies
make test           # run all 305+ tests
make lint           # black + ruff + mypy
make reproduce-paper1  # reproduce all deterministic paper results
```

## Questions

Open a GitHub issue for any question about the research, implementation, or
how to extend the system.

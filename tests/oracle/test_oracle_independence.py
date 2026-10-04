"""
The oracle must be independent of the system under test: no module in
jcl_oracle may import RELIC (legacy_contract), the baselines, or the
evaluation harness.
"""

import ast
from pathlib import Path

ORACLE = Path(__file__).resolve().parents[2] / "jcl_oracle"
FORBIDDEN = ("legacy_contract", "baselines", "relic_eval", "scripts")


def test_oracle_imports_nothing_from_relic():
    offenders = []
    for py in ORACLE.glob("*.py"):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for n in names:
                if n.split(".")[0] in FORBIDDEN:
                    offenders.append(f"{py.name}: {n}")
    assert offenders == []


def test_oracle_does_not_read_relic_outputs():
    # The oracle API takes JCL text (and subject procs / COBOL sources) only.
    import inspect
    from jcl_oracle.judge import compare_versions
    params = list(inspect.signature(compare_versions).parameters)
    assert params == ["original", "mutated", "proclib", "cobol_sources", "scenario_set"]

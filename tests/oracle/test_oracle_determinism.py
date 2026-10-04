"""
The oracle's verdicts (label, categories, evidence text) must not depend on the
per-process string hash seed. An earlier version paired behaviours by repr(),
which includes frozenset iteration order, so evidence and categories could
change between runs (found by comparing two clean reproductions).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = r"""
import json
from relic_eval.mutate import generate
from relic_eval.subjects import SUBJECTS
from jcl_oracle.judge import compare_versions
subj = SUBJECTS["carddemo"]
path = subj.root / "app/app-authorization-ims-db2-mq/jcl/DBPAUTP0.jcl"
orig = path.read_text(errors="replace")
out = []
for mu in generate(orig):
    if mu.operator == "SPLIT_JOB" and mu.text is not None:   # two jobs -> several behaviours
        out.append(compare_versions(orig, mu.text, subj.proclib, subj.cobol_sources).to_dict())
print(json.dumps(out, sort_keys=True))
"""


def _run(seed: str) -> list:
    env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=f"{ROOT / 'src'}{os.pathsep}{ROOT}")
    out = subprocess.run([sys.executable, "-c", SCRIPT], env=env, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_verdict_is_independent_of_hash_seed():
    results = [_run(seed) for seed in ("0", "1", "2", "12345", "987654")]
    assert results[0] and all(v["label"] == "DIFFERENT" for v in results[0])
    assert all(r == results[0] for r in results[1:])

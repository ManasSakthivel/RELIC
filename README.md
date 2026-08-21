# RELIC

Behavioral contract analysis for legacy software modernization.

When a COBOL/JCL system gets migrated to cloud-native infrastructure, structural dependency analysis can tell you what depends on what. What it can't tell you is whether the behavioral rules encoded in the original JCL — step ordering constraints, return-code guards, dataset dependencies — are still being enforced in the new system.

RELIC tries to make those implicit rules explicit, then check whether they're preserved.

---

## The problem

JCL job streams encode behavior that isn't written down as specifications. A step might only run if the previous one returned `RC=0`. A dataset might need to exist before a later step can use it. A return-code threshold might control whether an error branch fires.

When you migrate to Kubernetes or AWS Step Functions, these rules have to be reimplemented explicitly. It's easy to get them slightly wrong — and because the modernized system doesn't crash, the violation is silent.

Structural analysis catches things like "this step uses that dataset." It doesn't catch "this step's behavior changed because the condition that guards it was weakened."

---

## How RELIC works

```
JCL / COBOL artifacts
        │
        ├─ Parsing ─── JCL step structure, COBOL program references,
        │               return codes, dataset names
        │
        └─ Static extraction ── Behavioral Contract Graph (BCG)
                │                 Nodes: steps, programs, datasets
                │                 Edges: ordering constraints, data dependencies,
                │                        control-flow guards
                │
                ├─ Dynamic evidence ── execution traces (where available)
                │                       used to set contract confidence scores
                │
                └─ BCGDiff ── confidence-delta comparison across versions
                               flags contracts that are absent or weakened
```

The key idea is *confidence-delta differencing*: instead of just checking whether a contract exists in both versions, RELIC checks whether the contract has been *weakened* — e.g., a return-code threshold that changed from `RC=4` to `RC=16`. The structural graph looks identical in both versions; only the behavioral confidence changes.

---

## Results

Evaluated on the [AWS CardDemo](https://github.com/aws-samples/aws-mainframe-modernization-carddemo) COBOL codebase — 161 artifacts (55 JCL, 44 COBOL, 62 copybooks).

I generated mutations of the JCL control flow and ran each method against them:

| Method | F1 |
|---|---:|
| **RELIC** | **1.000** |
| Static BCG (no confidence-delta) | 0.960 |
| Structural dependency | 0.900 |
| Dependency + LLM† | 0.109 |
| LLM-only† | 0.038 |
| Complexity metrics | 0.000 |

RELIC detected 104/104 violating mutations and produced zero false positives on 144 semantics-preserving negatives.

† LLM baselines used blinded prompts but had substantial API failure rates (245/248 and 241/248 calls errored). The numbers above are lower bounds due to those failures.

**Scope note:** All of this is on CardDemo, a demonstration application. These aren't production numbers and shouldn't be read as "RELIC works on real mainframes." The methodology is sound on this benchmark; generalization to larger or more complex systems is an open question.

---

## Running it

```bash
git clone https://github.com/ManasSakthivel/RELIC.git
cd RELIC

pip install poetry
poetry install

make test               # 305 tests
make reproduce-paper1   # reproduce all deterministic results
```

Results are written to `results/rq1/`, `results/rq2/`, `results/rq3/`.

For LLM baselines (optional):
```bash
export GROQ_API_KEY="your-key"
python3.11 scripts/run_llm_baselines.py
```

No local GnuCOBOL installation required for the deterministic experiments.

---

## Repository structure

```
RELIC/
├── src/legacy_contract/   # core library — parsers, BCG, diff, reconciliation
├── baselines/             # comparison methods A–E
├── tests/                 # 305 unit and integration tests
├── datasets/              # CardDemo (Apache 2.0) + public COBOL
├── traces/                # execution traces used for dynamic evidence
├── benchmark/             # ground truth mutation annotations
├── experiments/           # frozen experiment configs
├── results/               # frozen results (JSON + CSV)
├── paper/                 # manuscript draft
└── docs/                  # architecture, methodology, limitations
```

---

## Limitations

- **Single dataset.** Everything is on CardDemo. It's a demonstration app, not a production system.
- **GnuCOBOL, not z/OS.** Dynamic evidence comes from GnuCOBOL 3.2 on Linux/macOS. 38 of 40 traces are JCL ordering simulations, not actual JCL execution.
- **TEMPORAL contracts only** for the independent RQ1 evaluation. RESOURCE and CONTROL_FLOW contracts require human annotation to evaluate independently.
- **FPR=0 is a closed-set result.** The negative benchmark is constructed from semantics-preserving mutations. It doesn't measure false positives in the open-world case.
- **LLM baseline results are lower bounds** due to API failures.

Full detail: [docs/limitations.md](docs/limitations.md)

---

## Paper

Manuscript: [`paper/paper.tex`](paper/paper.tex) — ACM sigconf format, under review.

---

## Citation

```bibtex
@misc{relic2025,
  title  = {RELIC: Execution-Grounded Behavioral Analysis for Legacy Software Modernization},
  author = {Manas Sakthivel},
  year   = {2025},
  url    = {https://github.com/ManasSakthivel/RELIC},
  note   = {Manuscript under review}
}
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).  
CardDemo dataset: Apache 2.0, copyright Amazon.com, Inc.

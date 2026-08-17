"""
Baseline C — LLM-Only Semantic Analysis.

Sends artifact source text plus a mutation description to an LLM and asks
whether the change introduces a semantic regression. No structural analysis,
no BCG, no provenance — pure LLM response.

Scientific purpose: tests whether an LLM alone, given source context, can match
the BCG approach for modernization-risk detection. The BCG approach is expected
to outperform this baseline for systematic detection because it provides explicit
contract structure, evidence chains, and dynamic grounding.

Provenance requirements (SCIENTIFIC INTEGRITY):
Every LLM call records:
    model, version, prompt_version, temperature, seed (if supported),
    input, output, timestamp, run_id.
LLM nondeterminism means results have variance across runs.
Run the experiment N_RUNS times and report mean ± std (default N_RUNS=5).

Graceful degradation:
If the OpenAI API key is not configured or the openai package is absent,
the baseline logs a warning and returns RESULT_UNAVAILABLE for that item.
The experiment runner marks affected results as [RESULT_PENDING].

NEVER fabricate LLM outputs. If the API is unavailable, report unavailability.

API compatibility: OpenAI Chat Completions (GPT-3.5-turbo / GPT-4).
The LLMAdapter interface is designed for easy swap to other providers.

Reference: Wei et al. (2022) "Chain-of-Thought Prompting Elicits Reasoning
           in Large Language Models" for prompting strategy.
           Brown et al. (2020) GPT-3 paper for few-shot prompting baseline.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Optional dependency
try:
    import openai as _openai
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False
    _openai = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Prompt versioning
# ---------------------------------------------------------------------------

# Prompt version is baked into results for exact reproducibility.
# Increment the version string whenever the prompt text changes.
PROMPT_VERSION = "v1.0.0"

SYSTEM_PROMPT = """\
You are a mainframe legacy software expert specializing in COBOL, JCL, and batch job
semantics. You analyze changes to legacy software for semantic regressions.

A semantic regression occurs when a code change causes the modernized system to
violate a behavioral obligation that existed in the original system — for example:
- A job that previously ran before another now runs after it (ordering violation)
- A file that was produced before consumption is no longer guaranteed (resource violation)
- An error-handling branch is removed or bypassed (control-flow violation)

Answer strictly in JSON with the following schema:
{
  "is_regression": true | false,
  "contract_type": "TEMPORAL" | "RESOURCE" | "CONTROL_FLOW" | "NONE",
  "confidence": 0.0 to 1.0,
  "explanation": "one or two sentences explaining your reasoning",
  "violated_contract": "concise statement of the behavioral obligation at risk"
}

Do not add any text outside the JSON object.
"""

USER_PROMPT_TEMPLATE = """\
ARTIFACT: {artifact_name}
ARTIFACT TYPE: {artifact_type}

ORIGINAL CODE:
```
{original_code}
```

MODIFIED CODE:
```
{modified_code}
```

CHANGE DESCRIPTION: {change_description}

Does this change introduce a semantic regression? Answer in the required JSON schema.
"""


# ---------------------------------------------------------------------------
# LLM response model
# ---------------------------------------------------------------------------

class LLMVerdict(str, Enum):
    REGRESSION = "REGRESSION"
    NOT_REGRESSION = "NOT_REGRESSION"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


@dataclass
class LLMAnalysisRecord:
    """
    Complete record of one LLM analysis call.

    SCIENTIFIC REQUIREMENT: All fields must be populated before any result is used.
    Do not use LLMVerdict.UNAVAILABLE results in metric computations.
    """
    record_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    run_id: str = ""
    artifact_name: str = ""
    artifact_type: str = ""
    change_description: str = ""
    # LLM provenance
    model: str = ""
    model_version: str = ""
    prompt_version: str = PROMPT_VERSION
    temperature: float = 0.0
    seed: int | None = None
    # Input/output (stored for reproducibility audit)
    llm_input: str = ""
    llm_output: str = ""
    # Parsed response
    verdict: LLMVerdict = LLMVerdict.UNAVAILABLE
    is_regression: bool = False
    contract_type: str = "NONE"
    llm_confidence: float = 0.0
    explanation: str = ""
    violated_contract: str = ""
    # Timing
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    latency_ms: float = 0.0
    # Error tracking
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "record_id": self.record_id,
            "run_id": self.run_id,
            "artifact_name": self.artifact_name,
            "artifact_type": self.artifact_type,
            "change_description": self.change_description,
            "model": self.model,
            "model_version": self.model_version,
            "prompt_version": self.prompt_version,
            "temperature": self.temperature,
            "seed": self.seed,
            "llm_input": self.llm_input,
            "llm_output": self.llm_output,
            "verdict": self.verdict.value,
            "is_regression": self.is_regression,
            "contract_type": self.contract_type,
            "llm_confidence": self.llm_confidence,
            "explanation": self.explanation,
            "violated_contract": self.violated_contract,
            "timestamp": self.timestamp,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }
        return d

    def input_hash(self) -> str:
        """SHA-256 of the LLM input for deduplication and reproducibility."""
        return hashlib.sha256(self.llm_input.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# LLM Adapter interface
# ---------------------------------------------------------------------------

class LLMAdapter:
    """
    Abstract LLM adapter. Swap implementations for different providers.
    Currently supports OpenAI Chat Completions.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        seed: int | None = 42,
        timeout: float = 30.0,
        max_tokens: int = 512,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.timeout = timeout
        self.max_tokens = max_tokens
        self._client: Any | None = None

        if _HAS_OPENAI:
            try:
                api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")
                base_url = os.getenv("OPENAI_BASE_URL")
                self._client = _openai.OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    timeout=self.timeout,
                )
            except Exception as exc:
                logger.warning(f"OpenAI client init failed: {exc}")
                self._client = None

    def is_available(self) -> bool:
        return self._client is not None and _HAS_OPENAI

    def call(self, user_message: str) -> tuple[str, float]:
        """
        Call the LLM with user_message.

        Returns (response_text, latency_ms).
        Raises RuntimeError if API is unavailable.
        """
        if not self.is_available():
            raise RuntimeError(
                "LLM API not available. Install openai and set OPENAI_API_KEY or "
                "GROQ_API_KEY. Configure OPENAI_BASE_URL for OpenAI-compatible providers."
            )

        t0 = time.monotonic()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.seed is not None:
            kwargs["seed"] = self.seed

        response = self._client.chat.completions.create(**kwargs)  # type: ignore[union-attr]
        latency_ms = (time.monotonic() - t0) * 1000.0
        content = response.choices[0].message.content or ""
        return content, latency_ms


# ---------------------------------------------------------------------------
# LLM-Only Baseline Analyzer
# ---------------------------------------------------------------------------

class LLMOnlyAnalyzer:
    """
    Baseline C: LLM-Only Semantic Analysis.

    For each (original_code, modified_code, change_description) tuple,
    calls the LLM and returns an LLMAnalysisRecord.

    Experiment configuration:
        N_RUNS = 5 to characterize variance (LLM nondeterminism)
        temperature = 0.0 for maximum determinism (seed is also set where supported)

    SCIENTIFIC NOTES:
    - Run with N_RUNS=5 minimum; report mean F1 ± std across runs.
    - Token cost is logged for reproducibility (see LLMAnalysisRecord.latency_ms).
    - Results with verdict=UNAVAILABLE must be excluded from metric computation.
    - temperature=0.0 reduces but does not eliminate nondeterminism.
    - Prompt version must be frozen before running held-out evaluation.
    """

    N_RUNS = 5  # Number of times to repeat each item for variance estimation

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        seed: int = 42,
        n_runs: int = 1,
    ) -> None:
        self._adapter = LLMAdapter(model=model, temperature=temperature, seed=seed)
        self._n_runs = n_runs
        self._model = model
        self._temperature = temperature
        self._seed = seed

    def analyze_item(
        self,
        artifact_name: str,
        artifact_type: str,
        original_code: str,
        modified_code: str,
        change_description: str,
        run_id: str = "",
    ) -> LLMAnalysisRecord:
        """
        Analyze a single change item for semantic regression.

        Returns one LLMAnalysisRecord with full provenance.
        If the LLM API is unavailable, returns a record with verdict=UNAVAILABLE.
        """
        record = LLMAnalysisRecord(
            run_id=run_id or str(uuid.uuid4())[:8],
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            change_description=change_description,
            model=self._model,
            temperature=self._temperature,
            seed=self._seed,
            prompt_version=PROMPT_VERSION,
        )

        user_message = USER_PROMPT_TEMPLATE.format(
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            original_code=original_code[:3000],    # Truncate to avoid token overflow
            modified_code=modified_code[:3000],
            change_description=change_description,
        )
        record.llm_input = user_message

        if not self._adapter.is_available():
            logger.warning(
                "LLM API unavailable. Marking result as UNAVAILABLE. "
                "Install openai and set OPENAI_API_KEY or GROQ_API_KEY to run Baseline C."
            )
            record.verdict = LLMVerdict.UNAVAILABLE
            record.error = "OpenAI API not configured."
            return record

        try:
            response_text, latency_ms = self._adapter.call(user_message)
            record.llm_output = response_text
            record.latency_ms = round(latency_ms, 1)
            self._parse_response(record, response_text)
        except Exception as exc:
            record.verdict = LLMVerdict.ERROR
            record.error = f"{type(exc).__name__}: {exc}"
            logger.error(f"LLM call failed for {artifact_name}: {exc}")

        return record

    def analyze_batch(
        self,
        items: list[dict[str, str]],
        run_id: str = "",
    ) -> list[LLMAnalysisRecord]:
        """
        Analyze a batch of change items.

        Each item must have keys:
            artifact_name, artifact_type, original_code, modified_code, change_description.

        Returns one LLMAnalysisRecord per item.
        """
        records = []
        run_id = run_id or str(uuid.uuid4())[:8]
        for item in items:
            record = self.analyze_item(
                artifact_name=item.get("artifact_name", ""),
                artifact_type=item.get("artifact_type", ""),
                original_code=item.get("original_code", ""),
                modified_code=item.get("modified_code", ""),
                change_description=item.get("change_description", ""),
                run_id=run_id,
            )
            records.append(record)
            # Rate-limit: 1 second between calls to avoid API quota exhaustion
            if self._adapter.is_available():
                time.sleep(1.0)
        return records

    def analyze_with_variance(
        self,
        artifact_name: str,
        artifact_type: str,
        original_code: str,
        modified_code: str,
        change_description: str,
        n_runs: int | None = None,
    ) -> tuple[list[LLMAnalysisRecord], dict[str, float]]:
        """
        Run the same item N_RUNS times to estimate variance.

        Returns (records, variance_stats).
        variance_stats keys: mean_confidence, std_confidence, agreement_rate,
                             regression_rate, n_available.

        SCIENTIFIC NOTE: Use this for reporting variance in the paper.
        Do not report only the first run as if it were deterministic.
        """
        n = n_runs or self._n_runs
        records = []
        for i in range(n):
            record = self.analyze_item(
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                original_code=original_code,
                modified_code=modified_code,
                change_description=change_description,
                run_id=f"var_run_{i}",
            )
            records.append(record)
            if self._adapter.is_available() and i < n - 1:
                time.sleep(1.0)

        available = [r for r in records if r.verdict != LLMVerdict.UNAVAILABLE]
        if not available:
            return records, {
                "mean_confidence": 0.0,
                "std_confidence": 0.0,
                "agreement_rate": 0.0,
                "regression_rate": 0.0,
                "n_available": 0,
            }

        confidences = [r.llm_confidence for r in available]
        regressions = [r.is_regression for r in available]
        mean_conf = sum(confidences) / len(confidences)
        n_a = len(available)
        std_conf = (
            (sum((c - mean_conf) ** 2 for c in confidences) / n_a) ** 0.5
            if n_a > 1 else 0.0
        )
        regression_rate = sum(regressions) / n_a
        # Agreement = fraction that agreed with majority verdict
        majority = regression_rate >= 0.5
        agreement = sum(1 for r in regressions if r == majority) / n_a

        stats = {
            "mean_confidence": round(mean_conf, 4),
            "std_confidence": round(std_conf, 4),
            "agreement_rate": round(agreement, 4),
            "regression_rate": round(regression_rate, 4),
            "n_available": n_a,
        }
        return records, stats

    def predictions_to_ids(
        self, records: list[LLMAnalysisRecord]
    ) -> list[str]:
        """
        Convert a list of LLMAnalysisRecords to a list of predicted-regression IDs
        for use with MetricsCalculator.compute().

        Only records with verdict=REGRESSION are included.
        Records with verdict=UNAVAILABLE or ERROR are excluded (not counted as negatives).
        """
        return [
            r.record_id
            for r in records
            if r.verdict == LLMVerdict.REGRESSION and r.is_regression
        ]

    # ------------------------------------------------------------------
    # Response parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(record: LLMAnalysisRecord, response_text: str) -> None:
        """
        Parse the LLM JSON response into record fields.

        If parsing fails, marks record.verdict = ERROR and records the raw output.
        The raw output is always preserved in record.llm_output for audit.
        """
        # Strip markdown code fences if present
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove opening and closing fence
            text = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            ).strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            record.verdict = LLMVerdict.ERROR
            record.error = f"JSON parse error: {exc}. Raw output: {response_text[:200]}"
            logger.warning(
                f"Could not parse LLM JSON response for {record.artifact_name}: {exc}"
            )
            return

        is_regression = bool(parsed.get("is_regression", False))
        record.is_regression = is_regression
        record.contract_type = str(parsed.get("contract_type", "NONE"))
        record.llm_confidence = float(parsed.get("confidence", 0.0))
        record.explanation = str(parsed.get("explanation", ""))
        record.violated_contract = str(parsed.get("violated_contract", ""))
        record.verdict = (
            LLMVerdict.REGRESSION if is_regression else LLMVerdict.NOT_REGRESSION
        )

    # ------------------------------------------------------------------
    # Logging / persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_records(records: list[LLMAnalysisRecord], output_path: str) -> None:
        """Save all LLM analysis records to a JSONL file for reproducibility audit."""
        from pathlib import Path
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record.to_dict(), default=str) + "\n")
        logger.info(f"Saved {len(records)} LLM records to {output_path}")

    @staticmethod
    def load_records(input_path: str) -> list[LLMAnalysisRecord]:
        """Load LLM analysis records from a JSONL file."""
        from pathlib import Path
        records = []
        p = Path(input_path)
        if not p.exists():
            return []
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    rec = LLMAnalysisRecord(
                        record_id=data.get("record_id", ""),
                        run_id=data.get("run_id", ""),
                        artifact_name=data.get("artifact_name", ""),
                        artifact_type=data.get("artifact_type", ""),
                        change_description=data.get("change_description", ""),
                        model=data.get("model", ""),
                        model_version=data.get("model_version", ""),
                        prompt_version=data.get("prompt_version", PROMPT_VERSION),
                        temperature=float(data.get("temperature", 0.0)),
                        seed=data.get("seed"),
                        llm_input=data.get("llm_input", ""),
                        llm_output=data.get("llm_output", ""),
                        verdict=LLMVerdict(data.get("verdict", "UNAVAILABLE")),
                        is_regression=bool(data.get("is_regression", False)),
                        contract_type=data.get("contract_type", "NONE"),
                        llm_confidence=float(data.get("llm_confidence", 0.0)),
                        explanation=data.get("explanation", ""),
                        violated_contract=data.get("violated_contract", ""),
                        timestamp=data.get("timestamp", ""),
                        latency_ms=float(data.get("latency_ms", 0.0)),
                        error=data.get("error"),
                    )
                    records.append(rec)
        return records

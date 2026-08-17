"""
Baseline D — Dependency-Augmented LLM Analysis.

First runs Baseline A (structural dependency analysis) to produce a concise
dependency context string, then passes that context together with the mutation
description to an LLM.  The hypothesis is that grounding the LLM in explicit
dependency information improves detection over Baseline C (LLM-only).

Scientific purpose: tests whether structural dependency context added to the LLM
prompt closes part of the gap between the LLM-only baseline and the full BCG
approach.  Compare Baseline D vs Baseline C to isolate the contribution of
structural grounding.

Prompt version: dep_llm_v1  (frozen — increment on any prompt text change)

LLM provenance (SCIENTIFIC INTEGRITY):
Every call records:
    model, prompt_version, temperature, seed, input_hash, output, timestamp.
Never fabricate outputs — if the API is unavailable, return stub result with
metadata["llm_available"] = False.

Graceful degradation:
If the openai package is absent OR the API key is not configured the baseline
operates in stub mode: predictions = {}, metadata["llm_available"] = False.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from legacy_contract.ir.model import IRGraph
from baselines.base import BaselineResult
from baselines.structural.structural import StructuralBaselineAnalyzer

logger = logging.getLogger(__name__)

# Optional dependency
try:
    import openai as _openai
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False
    _openai = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Prompt versioning (frozen)
# ---------------------------------------------------------------------------

PROMPT_VERSION: str = "dep_llm_v1"

_SYSTEM_PROMPT = """\
You are a mainframe legacy software expert specializing in COBOL, JCL, and batch job
semantics.  You analyze proposed changes to legacy systems for semantic regressions.

You are given:
1. A structural dependency summary of the affected artifact(s).
2. A description of the proposed change (mutation).

A semantic regression occurs when the change causes the modernized system to violate a
behavioral obligation that existed in the original:
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

_USER_PROMPT_TEMPLATE = """\
DEPENDENCY CONTEXT:
{dependency_context}

CHANGE DESCRIPTION:
{mutation_description}

Does this change introduce a semantic regression given the dependency context above?
Answer in the required JSON schema.
"""


# ---------------------------------------------------------------------------
# LLM call record
# ---------------------------------------------------------------------------

@dataclass
class DepLLMCallRecord:
    """Full provenance record for one LLM call made by DepLLMBaseline."""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    run_id: str = ""
    model: str = ""
    prompt_version: str = PROMPT_VERSION
    temperature: float = 0.0
    seed: int | None = None
    input_hash: str = ""
    llm_input: str = ""
    llm_output: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    latency_ms: float = 0.0
    error: str | None = None
    # Parsed result
    is_regression: bool = False
    contract_type: str = "NONE"
    llm_confidence: float = 0.0
    explanation: str = ""
    violated_contract: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":        self.record_id,
            "run_id":           self.run_id,
            "model":            self.model,
            "prompt_version":   self.prompt_version,
            "temperature":      self.temperature,
            "seed":             self.seed,
            "input_hash":       self.input_hash,
            "llm_input":        self.llm_input,
            "llm_output":       self.llm_output,
            "timestamp":        self.timestamp,
            "latency_ms":       self.latency_ms,
            "error":            self.error,
            "is_regression":    self.is_regression,
            "contract_type":    self.contract_type,
            "llm_confidence":   self.llm_confidence,
            "explanation":      self.explanation,
            "violated_contract": self.violated_contract,
        }


# ---------------------------------------------------------------------------
# Minimal LLM adapter (re-uses the openai client from Baseline C interface)
# ---------------------------------------------------------------------------

class _LLMAdapter:
    def __init__(
        self,
        model: str,
        temperature: float,
        seed: int | None,
        timeout: float = 30.0,
        max_tokens: int = 512,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self._client: Any = None
        if _HAS_OPENAI:
            try:
                api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")
                base_url = os.getenv("OPENAI_BASE_URL")
                self._client = _openai.OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    timeout=timeout,
                )  # type: ignore[union-attr]
            except Exception as exc:
                logger.warning(f"DepLLM: OpenAI client init failed: {exc}")
        self._max_tokens = max_tokens

    def is_available(self) -> bool:
        return self._client is not None and _HAS_OPENAI

    def call(self, user_message: str) -> tuple[str, float]:
        if not self.is_available():
            raise RuntimeError("LLM API not available.")
        t0 = time.monotonic()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            "temperature": self.temperature,
            "max_tokens":  self._max_tokens,
        }
        if self.seed is not None:
            kwargs["seed"] = self.seed
        response = self._client.chat.completions.create(**kwargs)
        latency_ms = (time.monotonic() - t0) * 1000.0
        content = response.choices[0].message.content or ""
        return content, latency_ms


# ---------------------------------------------------------------------------
# DepLLM Baseline
# ---------------------------------------------------------------------------

class DepLLMBaseline:
    """
    Baseline D: Dependency-Augmented LLM Analysis.

    1. Uses StructuralBaselineAnalyzer to build a dependency summary string.
    2. Passes that summary + mutation description to the LLM.
    3. Returns BaselineResult with per-contract predictions/confidences.

    Stub mode (LLM unavailable):
        predictions = {}
        metadata["llm_available"] = False
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        seed: int = 42,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._seed = seed
        self._adapter = _LLMAdapter(model, temperature, seed)
        self._analyzer = StructuralBaselineAnalyzer()
        self._call_log: list[DepLLMCallRecord] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(
        self,
        ir: IRGraph,
        mutation: Any,           # MutationRecord
        contract_ids: list[str],
        run_id: str = "",
    ) -> BaselineResult:
        """
        Predict violations for a set of contract IDs given a mutation.

        Parameters
        ----------
        ir:
            Full IRGraph for the artifact set.
        mutation:
            MutationRecord describing the applied change.
        contract_ids:
            All contract IDs to produce predictions for.
        run_id:
            Optional run identifier for provenance.

        Returns
        -------
        BaselineResult
        """
        run_id = run_id or str(uuid.uuid4())[:12]
        timestamp = datetime.now(tz=timezone.utc).isoformat()

        # Step 1: build dependency context via Baseline A
        sdg = self._analyzer.analyze(ir)
        dep_ctx = self._build_dependency_context(sdg, mutation)

        if not self._adapter.is_available():
            logger.warning(
                "DepLLM baseline: LLM API unavailable — returning stub result. "
                "Install openai and set OPENAI_API_KEY or GROQ_API_KEY."
            )
            return BaselineResult(
                method="dep_llm",
                predictions={},
                confidence={},
                metadata={
                    "llm_available":            False,
                    "prompt_version":           PROMPT_VERSION,
                    "model":                    self._model,
                    "dependency_context_length": len(dep_ctx),
                    "reason":                   "LLM API not configured.",
                },
                run_id=run_id,
                timestamp=timestamp,
            )

        # Step 2: call LLM
        call_record = self._call_llm(dep_ctx, mutation, run_id)
        self._call_log.append(call_record)

        # Step 3: map LLM verdict to per-contract predictions
        predictions: dict[str, bool] = {}
        confidence: dict[str, float] = {}
        for cid in contract_ids:
            predictions[cid] = call_record.is_regression
            confidence[cid] = round(call_record.llm_confidence, 4)

        return BaselineResult(
            method="dep_llm",
            predictions=predictions,
            confidence=confidence,
            metadata={
                "llm_available":            True,
                "prompt_version":           PROMPT_VERSION,
                "model":                    self._model,
                "temperature":              self._temperature,
                "seed":                     self._seed,
                "dependency_context_length": len(dep_ctx),
                "input_hash":               call_record.input_hash,
                "llm_record":               call_record.to_dict(),
            },
            run_id=run_id,
            timestamp=timestamp,
        )

    @property
    def call_log(self) -> list[DepLLMCallRecord]:
        """All LLM call records produced by this instance (for audit)."""
        return list(self._call_log)

    def save_call_log(self, output_path: str) -> None:
        """Persist all LLM call records to a JSONL file."""
        from pathlib import Path
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as fh:
            for rec in self._call_log:
                fh.write(json.dumps(rec.to_dict(), default=str) + "\n")
        logger.info(f"DepLLM: saved {len(self._call_log)} call records to {output_path}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_dependency_context(self, sdg: Any, mutation: Any) -> str:
        """
        Render a concise text summary of the structural dependency graph,
        focused on the entities affected by the mutation.
        """
        lines: list[str] = [
            "=== Structural Dependency Summary ===",
            f"Artifacts: {', '.join(sdg.artifact_paths) or '(none)'}",
            f"Total entities: {sdg.node_count()}",
            f"Total edges: {sdg.edge_count()}",
            "",
        ]

        # Highlight the affected entities
        affected_ids: list[str] = getattr(mutation, "affected_entity_ids", [])
        if affected_ids:
            lines.append("Affected entities and their immediate dependencies:")
            for eid in affected_ids:
                node = sdg.nodes.get(eid)
                name = node.name if node else eid
                etype = node.entity_type if node else "?"
                succs = sdg.successors(eid)
                preds = sdg.predecessors(eid)
                succ_names = [
                    (sdg.nodes[s].name if s in sdg.nodes else s) for s in succs[:5]
                ]
                pred_names = [
                    (sdg.nodes[p].name if p in sdg.nodes else p) for p in preds[:5]
                ]
                lines.append(
                    f"  [{etype}] {name}  "
                    f"depends-on: {pred_names or '[]'}  "
                    f"depended-by: {succ_names or '[]'}"
                )
            lines.append("")

        # Mutation description
        lines.append("=== Mutation ===")
        lines.append(f"Operator: {getattr(mutation, 'operator', '?')}")
        lines.append(f"Category: {getattr(mutation, 'failure_category', '?')}")
        lines.append(f"Original state: {getattr(mutation, 'original_state', '?')}")
        lines.append(f"Mutated state:  {getattr(mutation, 'mutated_state', '?')}")

        return "\n".join(lines)

    def _call_llm(
        self, dep_ctx: str, mutation: Any, run_id: str
    ) -> DepLLMCallRecord:
        """Execute one LLM call and return a fully populated DepLLMCallRecord."""
        mutation_desc = (
            f"Operator: {getattr(mutation, 'operator', '?')}\n"
            f"Category: {getattr(mutation, 'failure_category', '?')}\n"
            f"Original: {getattr(mutation, 'original_state', '?')}\n"
            f"Mutated:  {getattr(mutation, 'mutated_state', '?')}"
        )
        user_message = _USER_PROMPT_TEMPLATE.format(
            dependency_context=dep_ctx[:4000],   # guard against token overflow
            mutation_description=mutation_desc,
        )

        record = DepLLMCallRecord(
            run_id=run_id,
            model=self._model,
            prompt_version=PROMPT_VERSION,
            temperature=self._temperature,
            seed=self._seed,
            llm_input=user_message,
            input_hash=hashlib.sha256(user_message.encode()).hexdigest()[:16],
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

        try:
            response_text, latency_ms = self._adapter.call(user_message)
            record.llm_output = response_text
            record.latency_ms = round(latency_ms, 1)
            self._parse_response(record, response_text)
        except Exception as exc:
            record.error = f"{type(exc).__name__}: {exc}"
            logger.error(f"DepLLM call failed: {exc}")

        return record

    @staticmethod
    def _parse_response(record: DepLLMCallRecord, text: str) -> None:
        """Parse LLM JSON response into record fields."""
        text = text.strip()
        if text.startswith("```"):
            text = "\n".join(
                ln for ln in text.split("\n")
                if not ln.strip().startswith("```")
            ).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            record.error = f"JSON parse error: {exc}"
            logger.warning(f"DepLLM: could not parse response: {exc}")
            return
        record.is_regression    = bool(parsed.get("is_regression", False))
        record.contract_type    = str(parsed.get("contract_type", "NONE"))
        record.llm_confidence   = float(parsed.get("confidence", 0.0))
        record.explanation      = str(parsed.get("explanation", ""))
        record.violated_contract = str(parsed.get("violated_contract", ""))

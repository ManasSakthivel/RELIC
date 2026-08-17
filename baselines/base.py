"""
BaselineResult — common result dataclass shared by all baselines.

All baselines (A through E) must return a BaselineResult so that the
evaluation harness can compute metrics using a single code path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BaselineResult:
    method: str
    predictions: dict[str, bool]        # contract_id -> predicted_violated
    confidence: dict[str, float]         # contract_id -> confidence score [0,1]
    metadata: dict[str, Any] = field(default_factory=dict)
    run_id: str = ""
    timestamp: str = ""

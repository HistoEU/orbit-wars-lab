from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Issue:
    detector: str
    severity: str
    message: str
    match_id: str
    step: int | None = None
    slot: int | None = None
    evidence: dict[str, Any] | None = None

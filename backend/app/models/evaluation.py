from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationScore:
    skill_id: str
    rating: int
    note: str


@dataclass(frozen=True)
class EvaluationResult:
    scores: list[EvaluationScore]
    summary: str

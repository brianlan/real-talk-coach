from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

DRIFT_TOLERANCE_SECONDS = 2


def enforce_drift(
    client_timestamp: datetime,
    server_timestamp: datetime,
    *,
    tolerance_seconds: int = DRIFT_TOLERANCE_SECONDS,
) -> None:
    delta = abs((server_timestamp - client_timestamp).total_seconds())
    if delta > tolerance_seconds:
        raise ValueError(
            f"Timestamp drift {delta:.3f}s exceeds {tolerance_seconds}s tolerance"
        )


class PracticeSessionCreate(BaseModel):
    scenarioId: str = Field(..., min_length=1)
    clientSessionStartedAt: datetime


class TurnInput(BaseModel):
    sequence: int = Field(..., ge=0)
    audioBase64: str
    context: str | None = None
    startedAt: datetime
    endedAt: datetime

    @model_validator(mode="after")
    def validate_timestamps(self) -> "TurnInput":
        if self.endedAt < self.startedAt:
            raise ValueError("endedAt must be >= startedAt")
        return self

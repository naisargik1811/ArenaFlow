from __future__ import annotations
from pydantic import BaseModel, Field, field_validator


class FanAsk(BaseModel):
    query: str = Field(..., min_length=1, max_length=800)
    city: str | None = Field(default=None, max_length=80)

    @field_validator("query")
    @classmethod
    def _strip(cls, v: str) -> str:
        # Reject whitespace-only up front: strip first, then enforce non-empty,
        # because pydantic checks min_length=1 on the raw value before this runs.
        v = v.strip()
        if not v:
            raise ValueError("query must contain non-whitespace characters")
        return v


class FanAnswer(BaseModel):
    text: str
    language: str
    source: str
    model: str | None
    used_ids: list[str]


class OpsAsk(BaseModel):
    question: str = Field(..., min_length=1, max_length=800)
    venue: str = Field(..., min_length=1, max_length=80)
    minute: int = Field(default=60, ge=0, le=240)

    @field_validator("question")
    @classmethod
    def _strip_q(cls, v: str) -> str:
        # Mirror FanAsk: strip first, then enforce non-empty, because
        # pydantic checks min_length=1 on the raw value before this runs.
        v = v.strip()
        if not v:
            raise ValueError("question must contain non-whitespace characters")
        return v


class OpsAnswer(BaseModel):
    text: str
    source: str
    model: str | None
    used_ids: list[str]
    snapshot: dict

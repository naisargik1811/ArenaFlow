from __future__ import annotations
from pydantic import BaseModel, Field, field_validator

from arenaflow.core.llm import Reply


def _strip_nonempty(v: str, what: str) -> str:
    # Strip first, then enforce non-empty: pydantic checks min_length=1 on the
    # raw value before the validator runs, so a whitespace-only string slips past
    # min_length unless we strip and re-check here.
    v = v.strip()
    if not v:
        raise ValueError(f"{what} must contain non-whitespace characters")
    return v


class FanAsk(BaseModel):
    query: str = Field(..., min_length=1, max_length=800)
    city: str | None = Field(default=None, max_length=80)

    @field_validator("query")
    @classmethod
    def _strip(cls, v: str) -> str:
        return _strip_nonempty(v, "query")


class FanAnswer(Reply):
    language: str


class OpsAsk(BaseModel):
    question: str = Field(..., min_length=1, max_length=800)
    venue: str = Field(..., min_length=1, max_length=80)
    minute: int = Field(default=60, ge=0, le=240)

    @field_validator("question")
    @classmethod
    def _strip_q(cls, v: str) -> str:
        return _strip_nonempty(v, "question")


class OpsAnswer(Reply):
    snapshot: dict

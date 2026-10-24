"""Schemas for the optional AI assistant."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class AskRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={"example": {"question": "How many students are there?"}},
    )

    question: str = Field(..., min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def _clean(cls, value: str) -> str:
        value = _CONTROL_CHARS.sub("", value).strip()
        if not value:
            raise ValueError("question must not be empty")
        return value


class AskResponse(BaseModel):
    question: str
    answer: str
    source: Literal["sqlite"] = "sqlite"
    records_used: int = Field(..., description="Number of student records the answer is based on")
    method: Literal["deterministic", "llm", "deterministic_fallback", "none"] = Field(
        ...,
        description=(
            "How the answer was produced: 'deterministic' (computed from the database), "
            "'llm' (summarised by Ollama), 'deterministic_fallback' (LLM was needed but "
            "failed, so a plain database listing is returned), 'none' (question not understood)."
        ),
    )
    model: str | None = Field(None, description="Ollama model used; null unless method='llm'")
    warning: str | None = None

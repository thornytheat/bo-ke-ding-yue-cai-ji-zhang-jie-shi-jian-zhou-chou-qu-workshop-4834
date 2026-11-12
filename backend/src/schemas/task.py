from __future__ import annotations

from pydantic import BaseModel, Field


class TaskRunIn(BaseModel):
    mode: str = Field(default="both", pattern="^(ingest|parse|both)$")
    feed_codes: list[str] | None = Field(default=None, max_length=12)

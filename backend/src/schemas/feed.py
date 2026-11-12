from __future__ import annotations

from pydantic import BaseModel, Field


class FeedPatchIn(BaseModel):
    cadence: str | None = Field(default=None, max_length=32)
    host: str | None = Field(default=None, max_length=60)
    note: str | None = Field(default=None, max_length=400)
    active: bool | None = None

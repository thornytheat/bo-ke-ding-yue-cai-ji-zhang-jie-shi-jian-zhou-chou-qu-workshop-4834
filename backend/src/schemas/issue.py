from __future__ import annotations

from pydantic import BaseModel, Field


class IssueResolveIn(BaseModel):
    note: str = Field(default="", max_length=255)

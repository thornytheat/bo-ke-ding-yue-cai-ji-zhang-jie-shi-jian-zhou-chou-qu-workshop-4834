from __future__ import annotations

from pydantic import BaseModel, Field


class ChapterCreateIn(BaseModel):
    start_seconds: int | None = Field(default=None, ge=0, le=86400)
    raw_text: str | None = Field(default=None, max_length=500)
    title: str = Field(default="未命名章节", max_length=200)


class ChapterPatchIn(BaseModel):
    start_seconds: int | None = Field(default=None, ge=0, le=86400)
    raw_text: str | None = Field(default=None, max_length=500)
    title: str | None = Field(default=None, max_length=200)


class EpisodePatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=2000)

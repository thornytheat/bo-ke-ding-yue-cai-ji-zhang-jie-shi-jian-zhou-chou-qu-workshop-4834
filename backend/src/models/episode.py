"""单集（Episode）：show notes 原文是章节抽取的唯一输入，落库存快照哈希用于平台 diff。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"), index=True)
    guid: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    duration_seconds: Mapped[int] = mapped_column(Integer)
    published_on: Mapped[date] = mapped_column(Date, index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    show_notes: Mapped[str] = mapped_column(Text, default="")
    cover_hint: Mapped[str] = mapped_column(String(24), default="TAPE")
    season: Mapped[int] = mapped_column(Integer, default=1)
    episode_no: Mapped[int] = mapped_column(Integer, default=1)
    ingest_state: Mapped[str] = mapped_column(String(16), default="synced", index=True)
    parse_status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    chapter_count: Mapped[int] = mapped_column(Integer, default=0)
    unparsed_count: Mapped[int] = mapped_column(Integer, default=0)
    issue_count: Mapped[int] = mapped_column(Integer, default=0)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

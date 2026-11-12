"""采集/解析批次（DigestTask）：一次运行的可核对账本（扫了多少、新增/更新、异常几条）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class DigestTask(Base):
    __tablename__ = "digest_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(12), index=True)
    status: Mapped[str] = mapped_column(String(12), index=True, default="queued")
    feed_scope: Mapped[str] = mapped_column(String(160), default="all")
    triggered_by: Mapped[str] = mapped_column(String(160), default="")
    triggered_role: Mapped[str] = mapped_column(String(20), default="")

    feeds_scanned: Mapped[int] = mapped_column(Integer, default=0)
    episodes_scanned: Mapped[int] = mapped_column(Integer, default=0)
    episodes_new: Mapped[int] = mapped_column(Integer, default=0)
    episodes_updated: Mapped[int] = mapped_column(Integer, default=0)
    episodes_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    chapters_parsed: Mapped[int] = mapped_column(Integer, default=0)
    unparsed_chapters: Mapped[int] = mapped_column(Integer, default=0)
    issues_found: Mapped[int] = mapped_column(Integer, default=0)

    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    log_lines: Mapped[list] = mapped_column(JSON, default=list)
    error_text: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    seed_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

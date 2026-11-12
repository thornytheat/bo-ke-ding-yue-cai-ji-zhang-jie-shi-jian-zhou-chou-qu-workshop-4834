"""时间工具：统一 UTC 存储、按 Asia/Shanghai 展示（偏移 +480 分钟）。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

TZ_OFFSET_MINUTES = 480


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_now() -> datetime:
    return utcnow() + timedelta(minutes=TZ_OFFSET_MINUTES)


def local_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value + timedelta(minutes=TZ_OFFSET_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")


def date_iso(value) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d")

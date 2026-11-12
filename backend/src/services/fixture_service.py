"""确定性订阅源夹具读取：RSS XML / 平台 JSON / 目录 HTML。

夹具在资源目录里是静态快照，采集只读文件、不联网；解析失败抛 FixtureError，
由 digest_service 记进批次日志（不静默吞掉）。
"""
from __future__ import annotations

import html
import json
import pathlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import parsedate_to_datetime

ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
_ARTICLE = re.compile(r"<article\b([^>]*)>(.*?)</article>", re.S | re.I)
_ATTR = re.compile(r'data-([a-z_]+)="([^"]*)"', re.I)
_NOTES = re.compile(r'<pre class="show-notes">(.*?)</pre>', re.S | re.I)


class FixtureError(RuntimeError):
    """夹具缺失 / 结构与预期不符。"""


@dataclass
class EpisodeRecord:
    guid: str
    title: str
    duration_seconds: int
    published_on: date
    summary: str
    show_notes: str


def fixture_path(filename: str) -> pathlib.Path:
    # 延迟导入 settings：让纯解析函数可以在无 pydantic 的环境里单测
    from src.config.settings import settings

    return pathlib.Path(settings.fixture_dir) / filename


def _read_text(filename: str) -> str:
    path = fixture_path(filename)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:  # pragma: no cover - 夹具缺失时才会走到
        raise FixtureError(f"夹具不存在：{path}") from exc


def _duration_from_text(raw: str) -> int:
    raw = (raw or "").strip()
    if not raw:
        return 0
    if raw.isdigit():
        return int(raw)
    parts = [int(part) for part in raw.split(":") if part.strip().isdigit()]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return 0


def _parse_rss(text: str) -> list[EpisodeRecord]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise FixtureError(f"RSS XML 解析失败：{exc}") from exc

    records: list[EpisodeRecord] = []
    for item in root.findall("./channel/item"):
        guid = (item.findtext("guid") or "").strip()
        title = (item.findtext("title") or "").strip()
        notes = item.findtext("description") or ""
        summary = item.findtext(f"{ITUNES}summary") or ""
        duration = _duration_from_text(item.findtext(f"{ITUNES}duration") or "0")
        published = _parse_pub_date(item.findtext("pubDate"))
        if not guid or not title:
            continue
        records.append(
            EpisodeRecord(
                guid=guid,
                title=title,
                duration_seconds=duration,
                published_on=published,
                summary=summary.strip(),
                show_notes=notes.strip(),
            )
        )
    if not records:
        raise FixtureError("RSS 里没有任何 <item>")
    return records


def _parse_pub_date(raw: str | None) -> date:
    if not raw:
        return date(2026, 1, 1)
    try:
        return parsedate_to_datetime(raw.strip()).date()
    except (TypeError, ValueError):
        return datetime.strptime(raw.strip()[:10], "%Y-%m-%d").date()


def _parse_platform(text: str) -> list[EpisodeRecord]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FixtureError(f"平台 JSON 解析失败：{exc}") from exc

    episodes = payload.get("episodes") or []
    records: list[EpisodeRecord] = []
    for item in episodes:
        guid = str(item.get("id") or "").strip()
        title = str(item.get("title") or "").strip()
        if not guid or not title:
            continue
        records.append(
            EpisodeRecord(
                guid=guid,
                title=title,
                duration_seconds=int(item.get("duration_seconds") or 0),
                published_on=date.fromisoformat(str(item.get("published_on"))[:10]),
                summary=str(item.get("summary") or "").strip(),
                show_notes=str(item.get("notes") or "").strip(),
            )
        )
    if not records:
        raise FixtureError("平台响应里没有 episodes")
    return records


def _parse_catalog(text: str) -> list[EpisodeRecord]:
    records: list[EpisodeRecord] = []
    for attrs_raw, body in _ARTICLE.findall(text):
        attrs = {key.lower(): html.unescape(value) for key, value in _ATTR.findall(attrs_raw)}
        guid = (attrs.get("guid") or "").strip()
        title = (attrs.get("title") or "").strip()
        if not guid or not title:
            continue
        notes_match = _NOTES.search(body)
        notes = html.unescape(notes_match.group(1)).strip() if notes_match else ""
        records.append(
            EpisodeRecord(
                guid=guid,
                title=title,
                duration_seconds=int(attrs.get("duration") or 0),
                published_on=date.fromisoformat((attrs.get("published") or "2026-01-01")[:10]),
                summary=(attrs.get("summary") or "").strip(),
                show_notes=notes.replace("\r\n", "\n"),
            )
        )
    if not records:
        raise FixtureError("目录 HTML 里没有 <article class=episode>")
    return records


_READERS = {
    "rss": _parse_rss,
    "platform": _parse_platform,
    "apple": _parse_catalog,
}


def load_feed_records(feed) -> list[EpisodeRecord]:
    """按 feed.kind 选解析器；feed 可以是 ORM 对象或带同样字段的浅对象。"""
    reader = _READERS.get(feed.kind)
    if reader is None:  # pragma: no cover - 枚举受控
        raise FixtureError(f"未知订阅源类型：{feed.kind}")
    return reader(_read_text(feed.fixture_path))

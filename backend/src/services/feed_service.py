"""订阅源服务：列表聚合、配置维护、抓取预览（不落库的 diff）。"""
from __future__ import annotations

from sqlalchemy import func, select

from src.constants.enums import FEED_KIND_LABELS, INGEST_STATE_LABELS, IngestState
from src.models.chapter import Chapter
from src.models.chapter_issue import ChapterIssue
from src.models.episode import Episode
from src.models.feed import Feed
from src.services import fixture_service
from src.utils.errors import AppError
from src.utils.fingerprint import episode_fingerprint
from src.utils.timeutil import local_iso


def _episode_counts(db, feed_id: int) -> dict:
    episode_count = db.scalar(
        select(func.count()).select_from(Episode).where(Episode.feed_id == feed_id)
    ) or 0
    chapter_count = (
        db.scalar(
            select(func.count())
            .select_from(Chapter)
            .join(Episode, Episode.id == Chapter.episode_id)
            .where(Episode.feed_id == feed_id)
        )
        or 0
    )
    open_issues = (
        db.scalar(
            select(func.count())
            .select_from(ChapterIssue)
            .join(Episode, Episode.id == ChapterIssue.episode_id)
            .where(Episode.feed_id == feed_id, ChapterIssue.status == "open")
        )
        or 0
    )
    pending = db.scalar(
        select(func.count())
        .select_from(Episode)
        .where(Episode.feed_id == feed_id, Episode.ingest_state == IngestState.PENDING.value)
    ) or 0
    return {
        "episode_count": episode_count,
        "chapter_count": chapter_count,
        "open_issues": open_issues,
        "pending_episodes": pending,
    }


def feed_to_dict(db, feed: Feed) -> dict:
    counts = _episode_counts(db, feed.id)
    return {
        "id": feed.id,
        "code": feed.code,
        "name": feed.name,
        "show_name": feed.show_name,
        "kind": feed.kind,
        "kind_label": FEED_KIND_LABELS.get(feed.kind, feed.kind),
        "url": feed.url,
        "fixture_path": feed.fixture_path,
        "cadence": feed.cadence,
        "host": feed.host,
        "active": feed.active,
        "last_fetch_at": local_iso(feed.last_fetch_at),
        "last_status": feed.last_status,
        "last_episode_count": feed.last_episode_count,
        "note": feed.note,
        **counts,
    }


def list_feeds(db) -> list[dict]:
    feeds = list(db.scalars(select(Feed).order_by(Feed.sort_order)))
    return [feed_to_dict(db, feed) for feed in feeds]


def get_feed(db, code: str) -> Feed:
    feed = db.scalar(select(Feed).where(Feed.code == code))
    if feed is None:
        raise AppError("NOT_FOUND", 404, detail=f"feed={code}")
    return feed


def update_feed(db, code: str, payload: dict) -> dict:
    feed = get_feed(db, code)
    for field in ("cadence", "host", "note"):
        if payload.get(field) is not None:
            setattr(feed, field, str(payload[field])[:160])
    if payload.get("active") is not None:
        feed.active = bool(payload["active"])
    db.flush()
    return feed_to_dict(db, feed)


def preview_feed(db, code: str) -> dict:
    """抓取预览：读夹具、按指纹比对，返回会新增/更新/不变的清单（不落库）。"""
    feed = get_feed(db, code)
    try:
        records = fixture_service.load_feed_records(feed)
    except fixture_service.FixtureError as exc:
        raise AppError("FEED_INACTIVE", 422, detail=str(exc)) from exc

    episodes = {
        episode.guid: episode
        for episode in db.scalars(select(Episode).where(Episode.feed_id == feed.id))
    }
    created: list[dict] = []
    updated: list[dict] = []
    unchanged = 0
    for record in records:
        fingerprint = episode_fingerprint(
            record.title, record.summary, record.duration_seconds, record.show_notes
        )
        episode = episodes.get(record.guid)
        if episode is None:
            created.append(
                {"guid": record.guid, "title": record.title, "published_on": record.published_on.isoformat()}
            )
            continue
        if episode.ingest_state == IngestState.PENDING.value:
            created.append(
                {
                    "guid": record.guid,
                    "title": record.title,
                    "published_on": record.published_on.isoformat(),
                    "episode_code": episode.code,
                    "reason": "水位线后新到达，尚未入库采集",
                }
            )
            continue
        if episode.content_hash != fingerprint:
            updated.append(
                {
                    "guid": record.guid,
                    "episode_code": episode.code,
                    "title": record.title,
                    "changes": _diff_fields(episode, record),
                }
            )
            continue
        unchanged += 1

    return {
        "feed": feed_to_dict(db, feed),
        "scanned": len(records),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "ingest_state_labels": INGEST_STATE_LABELS,
    }


def _diff_fields(episode: Episode, record) -> list[dict]:
    changes: list[dict] = []
    if (episode.title or "").strip() != record.title.strip():
        changes.append({"field": "title", "from": episode.title, "to": record.title})
    if (episode.summary or "").strip() != record.summary.strip():
        changes.append(
            {"field": "summary", "from": (episode.summary or "")[:90], "to": record.summary[:90]}
        )
    if int(episode.duration_seconds or 0) != int(record.duration_seconds or 0):
        changes.append(
            {
                "field": "duration_seconds",
                "from": episode.duration_seconds,
                "to": record.duration_seconds,
            }
        )
    if (episode.show_notes or "").strip() != record.show_notes.strip():
        changes.append({"field": "show_notes", "from": "（旧版 show notes）", "to": "（新版 show notes）"})
    if not changes:
        changes.append({"field": "content_hash", "from": "旧指纹", "to": "新指纹"})
    return changes

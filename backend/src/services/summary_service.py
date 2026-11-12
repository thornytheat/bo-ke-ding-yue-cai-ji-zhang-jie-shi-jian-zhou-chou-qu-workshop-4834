"""顶部看板聚合：一次请求给出全站口径（节目库/异常队列/采集页共用）。"""
from __future__ import annotations

from sqlalchemy import func, select

from src.constants.enums import IngestState, IssueStatus, ParseStatus, TaskStatus
from src.models.chapter import Chapter
from src.models.chapter_issue import ChapterIssue
from src.models.digest_task import DigestTask
from src.models.episode import Episode
from src.models.feed import Feed
from src.services import issue_service
from src.utils.timeutil import local_iso


def overview(db) -> dict:
    feeds = db.scalar(select(func.count()).select_from(Feed)) or 0
    active_feeds = db.scalar(select(func.count()).select_from(Feed).where(Feed.active.is_(True))) or 0
    episodes = db.scalar(select(func.count()).select_from(Episode)) or 0
    chapters = db.scalar(select(func.count()).select_from(Chapter)) or 0
    unparsed_chapters = (
        db.scalar(
            select(func.count()).select_from(Chapter).where(Chapter.start_seconds.is_(None))
        )
        or 0
    )
    ambiguous = (
        db.scalar(select(func.count()).select_from(Chapter).where(Chapter.ambiguous.is_(True))) or 0
    )
    pending_ingest = (
        db.scalar(
            select(func.count())
            .select_from(Episode)
            .where(Episode.ingest_state == IngestState.PENDING.value)
        )
        or 0
    )
    partial_parse = (
        db.scalar(
            select(func.count())
            .select_from(Episode)
            .where(Episode.parse_status == ParseStatus.PARTIAL.value)
        )
        or 0
    )
    issue_counts = issue_service.issue_summary(db)
    running = db.scalar(
        select(func.count())
        .select_from(DigestTask)
        .where(DigestTask.status.in_([TaskStatus.QUEUED.value, TaskStatus.RUNNING.value]))
    ) or 0
    latest = db.scalar(select(DigestTask).order_by(DigestTask.id.desc()).limit(1))
    return {
        "feeds": feeds,
        "active_feeds": active_feeds,
        "episodes": episodes,
        "chapters": chapters,
        "unparsed_chapters": unparsed_chapters,
        "ambiguous_chapters": ambiguous,
        "pending_ingest": pending_ingest,
        "partial_parse": partial_parse,
        "open_issues": issue_counts["open"],
        "resolved_issues": issue_counts["resolved"],
        "total_issues": issue_counts["total"],
        "gap_issues": issue_counts["gap"],
        "running_tasks": running,
        "issues_by_kind": issue_counts["by_kind"],
        "latest_task": (
            {
                "code": latest.code,
                "mode": latest.mode,
                "status": latest.status,
                "finished_at": local_iso(latest.finished_at),
                "episodes_scanned": latest.episodes_scanned,
                "chapters_parsed": latest.chapters_parsed,
                "issues_found": latest.issues_found,
            }
            if latest
            else None
        ),
    }


def episode_parse_breakdown(db) -> list[dict]:
    rows = db.execute(
        select(Episode.parse_status, func.count()).group_by(Episode.parse_status)
    ).all()
    return [{"status": status, "count": count} for status, count in rows]

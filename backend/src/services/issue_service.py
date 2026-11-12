"""异常工单服务：校验结果 ↔ chapter_issues 的同步、列表、处置、全量复扫。"""
from __future__ import annotations

from sqlalchemy import Select, delete, func, select

from src.constants.enums import (
    ISSUE_KIND_LABELS,
    ISSUE_KIND_ORDER,
    IssueKind,
    IssueStatus,
)
from src.models.chapter import Chapter
from src.models.chapter_issue import ChapterIssue
from src.models.episode import Episode
from src.models.feed import Feed
from src.services import validation_service
from src.utils.errors import AppError
from src.utils.timecode import to_short_timecode
from src.utils.timeutil import utcnow


def sync_episode_issues(db, episode: Episode) -> int:
    """把一集的校验结果同步进工单表；重复校验不产生重复工单，消失的工单自动归档。"""
    chapters = list(
        db.scalars(select(Chapter).where(Chapter.episode_id == episode.id).order_by(Chapter.ordinal))
    )
    result = validation_service.validate_episode(
        episode.code,
        episode.duration_seconds,
        validation_service.chapter_inputs(chapters),
    )

    existing = {
        row.issue_key: row
        for row in db.scalars(select(ChapterIssue).where(ChapterIssue.episode_id == episode.id))
    }
    seen: set[str] = set()
    for draft in result.issues:
        seen.add(draft.issue_key)
        row = existing.get(draft.issue_key)
        if row is None:
            db.add(
                ChapterIssue(
                    issue_key=draft.issue_key,
                    episode_id=episode.id,
                    chapter_id=draft.chapter_id,
                    kind=draft.kind,
                    status=IssueStatus.OPEN.value,
                    severity=draft.severity,
                    message=draft.message,
                    suggestion=draft.suggestion,
                    window_start=draft.window_start,
                    window_end=draft.window_end,
                    detected_by="validator",
                )
            )
            continue
        row.message = draft.message
        row.suggestion = draft.suggestion
        row.severity = draft.severity
        row.window_start = draft.window_start
        row.window_end = draft.window_end

    for key, row in existing.items():
        if key in seen or row.status == IssueStatus.RESOLVED.value:
            continue
        row.status = IssueStatus.RESOLVED.value
        row.resolved_by = "system:rescan"
        row.resolved_at = utcnow()
        row.resolution_note = "重新校验未再出现"

    db.flush()
    episode.issue_count = (
        db.scalar(
            select(func.count())
            .select_from(ChapterIssue)
            .where(ChapterIssue.episode_id == episode.id, ChapterIssue.status == IssueStatus.OPEN.value)
        )
        or 0
    )
    return episode.issue_count


def purge_for_chapters(db, chapter_ids: list[int]) -> int:
    """章节行被删除/重建前，先清掉引用它的工单，避免外键阻塞（工单随后由校验重建）。"""
    ids = [chapter_id for chapter_id in chapter_ids if chapter_id is not None]
    if not ids:
        return 0
    result = db.execute(delete(ChapterIssue).where(ChapterIssue.chapter_id.in_(ids)))
    db.flush()
    return result.rowcount or 0


def _issue_query(
    kind: str | None,
    status: str | None,
    episode_code: str | None,
    feed_code: str | None,
) -> Select:
    stmt = (
        select(ChapterIssue, Episode, Feed)
        .join(Episode, Episode.id == ChapterIssue.episode_id)
        .join(Feed, Feed.id == Episode.feed_id)
    )
    if kind:
        stmt = stmt.where(ChapterIssue.kind == kind)
    if status:
        stmt = stmt.where(ChapterIssue.status == status)
    if episode_code:
        stmt = stmt.where(Episode.code == episode_code)
    if feed_code:
        stmt = stmt.where(Feed.code == feed_code)
    return stmt


def list_issues(
    db,
    kind: str | None = None,
    status: str | None = None,
    episode_code: str | None = None,
    feed_code: str | None = None,
    page: int = 1,
    size: int = 50,
) -> dict:
    base = _issue_query(kind, status, episode_code, feed_code)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(ChapterIssue.status.asc(), ChapterIssue.kind.asc(), ChapterIssue.id.asc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    chapter_ids = [issue.chapter_id for issue, _, _ in rows if issue.chapter_id]
    chapters = {
        chapter.id: chapter
        for chapter in db.scalars(select(Chapter).where(Chapter.id.in_(chapter_ids)))
    } if chapter_ids else {}

    items = []
    for issue, episode, feed in rows:
        chapter = chapters.get(issue.chapter_id) if issue.chapter_id else None
        items.append(
            {
                "id": issue.id,
                "issue_key": issue.issue_key,
                "kind": issue.kind,
                "kind_label": ISSUE_KIND_LABELS.get(issue.kind, issue.kind),
                "status": issue.status,
                "severity": issue.severity,
                "message": issue.message,
                "suggestion": issue.suggestion,
                "window_start": issue.window_start,
                "window_end": issue.window_end,
                "window_start_tc": to_short_timecode(issue.window_start) if issue.window_start is not None else None,
                "episode_code": episode.code,
                "episode_id": episode.id,
                "episode_title": episode.title,
                "feed_code": feed.code,
                "feed_name": feed.name,
                "chapter_id": issue.chapter_id,
                "chapter_title": chapter.title if chapter else "",
                "chapter_time_tc": (
                    to_short_timecode(chapter.start_seconds)
                    if chapter and chapter.start_seconds is not None
                    else None
                ),
                "resolved_by": issue.resolved_by,
                "resolution_note": issue.resolution_note,
                "created_at": issue.created_at.strftime("%Y-%m-%d %H:%M") if issue.created_at else None,
            }
        )

    return {"items": items, "total": total, "page": page, "size": size}


def issue_summary(db) -> dict:
    kind_rows = db.execute(
        select(ChapterIssue.kind, ChapterIssue.status, func.count())
        .group_by(ChapterIssue.kind, ChapterIssue.status)
    ).all()
    counts: dict[str, dict[str, int]] = {kind: {"open": 0, "resolved": 0} for kind in ISSUE_KIND_ORDER}
    for kind, status, count in kind_rows:
        counts.setdefault(kind, {"open": 0, "resolved": 0})
        counts[kind][status] = counts[kind].get(status, 0) + count

    open_total = sum(item["open"] for item in counts.values())
    resolved_total = sum(item["resolved"] for item in counts.values())
    by_kind = [
        {
            "kind": kind,
            "label": ISSUE_KIND_LABELS.get(kind, kind),
            "open": counts.get(kind, {}).get("open", 0),
            "resolved": counts.get(kind, {}).get("resolved", 0),
            "total": counts.get(kind, {}).get("open", 0) + counts.get(kind, {}).get("resolved", 0),
        }
        for kind in ISSUE_KIND_ORDER
    ]
    return {
        "open": open_total,
        "resolved": resolved_total,
        "total": open_total + resolved_total,
        "by_kind": by_kind,
        "gap": counts.get(IssueKind.GAP_WARNING.value, {}).get("open", 0),
        "unparsed": counts.get(IssueKind.UNPARSED.value, {}).get("open", 0),
    }


def resolve_issue(db, issue_id: int, note: str, actor_email: str) -> dict:
    issue = db.get(ChapterIssue, issue_id)
    if issue is None:
        raise AppError("NOT_FOUND", 404, detail=f"issue={issue_id}")
    if issue.status == IssueStatus.RESOLVED.value:
        raise AppError("CONFLICT", 409, detail="该异常已处置")
    issue.status = IssueStatus.RESOLVED.value
    issue.resolved_by = actor_email
    issue.resolved_at = utcnow()
    issue.resolution_note = (note or "人工确认")[:255]
    db.flush()

    episode = db.get(Episode, issue.episode_id)
    if episode is not None:
        episode.issue_count = (
            db.scalar(
                select(func.count())
                .select_from(ChapterIssue)
                .where(
                    ChapterIssue.episode_id == episode.id,
                    ChapterIssue.status == IssueStatus.OPEN.value,
                )
            )
            or 0
        )
    return {"id": issue.id, "status": issue.status, "resolution_note": issue.resolution_note}


def rescan_all(db) -> dict:
    episodes = list(db.scalars(select(Episode).order_by(Episode.code)))
    for episode in episodes:
        sync_episode_issues(db, episode)
    return {"episodes": len(episodes), **issue_summary(db)}

"""单集服务：列表/详情/原文对照/重解析/不变量修正。"""
from __future__ import annotations

from sqlalchemy import func, or_, select

from src.constants.enums import (
    CHAPTER_SOURCE_LABELS,
    ISSUE_KIND_LABELS,
    PARSE_STATUS_LABELS,
    ChapterSource,
    IssueStatus,
    ParseStatus,
)
from src.models.chapter import Chapter
from src.models.chapter_issue import ChapterIssue
from src.models.episode import Episode
from src.models.feed import Feed
from src.services import digest_service, issue_service, parse_service, validation_service
from src.utils.errors import AppError
from src.utils.timecode import human_duration, to_short_timecode, to_timecode
from src.utils.timeutil import local_iso


def _episode_brief(db, episode: Episode, feed: Feed) -> dict:
    return {
        "id": episode.id,
        "code": episode.code,
        "title": episode.title,
        "feed_code": feed.code,
        "feed_name": feed.name,
        "show_name": feed.show_name,
        "season": episode.season,
        "episode_no": episode.episode_no,
        "duration_seconds": episode.duration_seconds,
        "duration_tc": to_timecode(episode.duration_seconds),
        "published_on": episode.published_on.isoformat() if episode.published_on else None,
        "summary": episode.summary,
        "cover_hint": episode.cover_hint,
        "ingest_state": episode.ingest_state,
        "parse_status": episode.parse_status,
        "parse_status_label": PARSE_STATUS_LABELS.get(episode.parse_status, episode.parse_status),
        "chapter_count": episode.chapter_count,
        "unparsed_count": episode.unparsed_count,
        "issue_count": episode.issue_count,
        "parsed_at": local_iso(episode.parsed_at),
    }


def list_episodes(
    db,
    feed_code: str | None = None,
    parse_status: str | None = None,
    ingest_state: str | None = None,
    query: str | None = None,
    page: int = 1,
    size: int = 24,
) -> dict:
    stmt = select(Episode, Feed).join(Feed, Feed.id == Episode.feed_id)
    if feed_code:
        stmt = stmt.where(Feed.code == feed_code)
    if parse_status:
        stmt = stmt.where(Episode.parse_status == parse_status)
    if ingest_state:
        stmt = stmt.where(Episode.ingest_state == ingest_state)
    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where(or_(Episode.title.like(like), Episode.code.like(like), Feed.show_name.like(like)))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(Episode.published_on.desc(), Episode.code.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return {
        "items": [_episode_brief(db, episode, feed) for episode, feed in rows],
        "total": total,
        "page": page,
        "size": size,
    }


def get_episode(db, code: str) -> tuple[Episode, Feed]:
    row = db.execute(
        select(Episode, Feed).join(Feed, Feed.id == Episode.feed_id).where(Episode.code == code)
    ).first()
    if row is None:
        raise AppError("NOT_FOUND", 404, detail=f"episode={code}")
    return row[0], row[1]


def _chapters_of(db, episode: Episode) -> list[Chapter]:
    return list(
        db.scalars(
            select(Chapter).where(Chapter.episode_id == episode.id).order_by(Chapter.ordinal, Chapter.id)
        )
    )


def chapter_to_dict(chapter: Chapter, duration_seconds: int, next_start: int | None) -> dict:
    start = chapter.start_seconds
    end = next_start if next_start is not None else duration_seconds
    window = (end - start) if (start is not None and end >= start) else None
    return {
        "id": chapter.id,
        "ordinal": chapter.ordinal,
        "start_seconds": start,
        "start_tc": to_short_timecode(start) if start is not None else None,
        "start_full_tc": to_timecode(start) if start is not None else None,
        "title": chapter.title,
        "raw_text": chapter.raw_text,
        "parse_rule": chapter.parse_rule,
        "confidence": round(chapter.confidence or 0.0, 3),
        "ambiguous": chapter.ambiguous,
        "source": chapter.source,
        "source_label": CHAPTER_SOURCE_LABELS.get(chapter.source, chapter.source),
        "auto_fixed": chapter.auto_fixed,
        "fix_note": chapter.fix_note,
        "window_seconds": window,
        "window_human": human_duration(window) if window is not None else "—",
    }


def chapters_view(db, episode: Episode) -> list[dict]:
    chapters = _chapters_of(db, episode)
    starts = [c.start_seconds for c in chapters if c.start_seconds is not None]
    ordered = sorted(starts)
    result: list[dict] = []
    for chapter in chapters:
        next_start = None
        if chapter.start_seconds is not None:
            greater = [value for value in ordered if value > chapter.start_seconds]
            next_start = greater[0] if greater else None
        result.append(chapter_to_dict(chapter, episode.duration_seconds, next_start))
    return result


def _notes_view(episode: Episode) -> list[dict]:
    lines: list[dict] = []
    for index, line in enumerate((episode.show_notes or "").splitlines()):
        entry = parse_service.parse_line(line, episode.duration_seconds)
        if entry is None:
            lines.append({"line_no": index + 1, "text": line, "state": "ignored"})
            continue
        lines.append(
            {
                "line_no": index + 1,
                "text": line,
                "state": "unparsed" if entry.seconds is None else "parsed",
                "seconds": entry.seconds,
                "time_tc": to_short_timecode(entry.seconds) if entry.seconds is not None else None,
                "title": entry.title,
                "rule": entry.rule,
                "confidence": entry.confidence,
                "ambiguous": entry.ambiguous,
            }
        )
    return lines


def _open_issue_view(db, episode: Episode) -> list[dict]:
    rows = list(
        db.scalars(
            select(ChapterIssue)
            .where(ChapterIssue.episode_id == episode.id)
            .order_by(ChapterIssue.kind, ChapterIssue.window_start)
        )
    )
    return [
        {
            "id": row.id,
            "kind": row.kind,
            "kind_label": ISSUE_KIND_LABELS.get(row.kind, row.kind),
            "status": row.status,
            "severity": row.severity,
            "message": row.message,
            "suggestion": row.suggestion,
            "window_start_tc": to_short_timecode(row.window_start) if row.window_start is not None else None,
            "resolution_note": row.resolution_note,
        }
        for row in rows
        if row.status == IssueStatus.OPEN.value
    ]


def episode_detail(db, code: str) -> dict:
    episode, feed = get_episode(db, code)
    chapters = chapters_view(db, episode)
    validation = validation_service.validate_episode(
        episode.code,
        episode.duration_seconds,
        validation_service.chapter_inputs(_chapters_of(db, episode)),
    )
    return {
        "episode": _episode_brief(db, episode, feed),
        "feed": {
            "code": feed.code,
            "name": feed.name,
            "show_name": feed.show_name,
            "kind": feed.kind,
            "host": feed.host,
            "cadence": feed.cadence,
        },
        "chapters": chapters,
        "show_notes": episode.show_notes,
        "notes_lines": _notes_view(episode),
        "issues": _open_issue_view(db, episode),
        "validation": validation.to_plan(),
    }


def reparse_episode(db, code: str) -> dict:
    episode, _ = get_episode(db, code)
    stats = digest_service.rebuild_chapters(db, episode)
    open_issues = issue_service.sync_episode_issues(db, episode)
    return {
        "episode_code": episode.code,
        "entries": stats["entries"],
        "unparsed": stats["unparsed"],
        "ambiguous": stats["ambiguous"],
        "rule_usage": stats["rule_usage"],
        "about_minutes": stats["about_minutes"],
        "open_issues": open_issues,
    }


def normalize_episode(db, code: str) -> dict:
    """把不变量校验给出的修正表落到库里：重排 / 合并重叠 / 折叠过短。"""
    episode, _ = get_episode(db, code)
    chapters = _chapters_of(db, episode)
    validation = validation_service.validate_episode(
        episode.code,
        episode.duration_seconds,
        validation_service.chapter_inputs(chapters),
    )

    by_id = {chapter.id: chapter for chapter in chapters}
    unparsed_rows = [chapter for chapter in chapters if chapter.start_seconds is None]
    kept: list[Chapter] = []
    for corrected in validation.corrected:
        row = by_id.get(corrected.chapter_id)
        if row is None:
            continue
        row.start_seconds = corrected.start_seconds
        row.title = corrected.title
        if corrected.auto_fixed:
            row.auto_fixed = True
            row.fix_note = corrected.fix_note[:200]
        kept.append(row)

    kept_ids = {row.id for row in kept}
    drop_ids = [chapter.id for chapter in chapters if chapter.id not in kept_ids]
    issue_service.purge_for_chapters(db, drop_ids)
    deleted = 0
    for chapter in chapters:
        if chapter.id in kept_ids:
            continue
        if chapter.start_seconds is None and chapter in unparsed_rows:
            kept.append(chapter)
            continue
        db.delete(chapter)
        deleted += 1
    db.flush()

    kept.sort(
        key=lambda row: (
            row.start_seconds is None,
            row.start_seconds if row.start_seconds is not None else 0,
            row.ordinal,
        )
    )
    for index, row in enumerate(kept):
        row.ordinal = index
    db.flush()

    episode.chapter_count = len(kept)
    episode.unparsed_count = sum(1 for row in kept if row.start_seconds is None)
    episode.parse_status = (
        ParseStatus.PARSED.value
        if episode.unparsed_count == 0
        else (ParseStatus.PARTIAL.value if episode.unparsed_count < len(kept) else ParseStatus.FAILED.value)
    )
    open_issues = issue_service.sync_episode_issues(db, episode)

    return {
        "episode_code": episode.code,
        "reordered": validation.reordered,
        "merged": validation.merged,
        "folded": validation.folded,
        "deleted_rows": deleted,
        "gaps": validation.gaps,
        "open_issues": open_issues,
        "chapters": chapters_view(db, episode),
    }


def chapter_source_values() -> list[str]:
    return [item.value for item in ChapterSource]

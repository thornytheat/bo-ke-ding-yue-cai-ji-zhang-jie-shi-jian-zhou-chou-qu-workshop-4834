"""章节服务：内联编辑（人工补录/改时间点/改标题/删除）与越界、重复点校验。"""
from __future__ import annotations

from sqlalchemy import select

from src.constants.enums import ChapterSource
from src.constants.limits import MAX_CHAPTERS_PER_EPISODE
from src.models.chapter import Chapter
from src.services import episode_service, issue_service, parse_service
from src.utils.errors import AppError
from src.utils.timecode import to_short_timecode


def _chapters(db, episode_id: int) -> list[Chapter]:
    return list(
        db.scalars(
            select(Chapter).where(Chapter.episode_id == episode_id).order_by(Chapter.ordinal, Chapter.id)
        )
    )


def _resequence(db, episode_id: int) -> None:
    rows = _chapters(db, episode_id)
    rows.sort(
        key=lambda row: (
            row.start_seconds is None,
            row.start_seconds if row.start_seconds is not None else 0,
            row.ordinal,
        )
    )
    for index, row in enumerate(rows):
        row.ordinal = index
    db.flush()


def _resolve_seconds(episode, payload: dict, current: int | None = None) -> tuple[int | None, dict]:
    """三种输入方式：直接给秒 / 给原始时间码让后端解析 / 只改标题。"""
    meta: dict = {"rule": "", "confidence": 1.0, "ambiguous": False}
    raw = (payload.get("raw_text") or "").strip()
    if raw:
        entry = parse_service.parse_timestamp(raw, episode.duration_seconds)
        if entry is None or entry.seconds is None:
            raise AppError(
                "VALIDATION",
                422,
                detail="无法从原文识别时间码，请直接填 start_seconds 或改用 mm:ss / hh:mm:ss",
            )
        meta = {
            "rule": entry.rule,
            "confidence": entry.confidence,
            "ambiguous": entry.ambiguous,
        }
        return entry.seconds, meta
    if payload.get("start_seconds") is not None:
        seconds = int(payload["start_seconds"])
        return seconds, meta
    return current, meta


def _assert_range(episode, seconds: int | None) -> None:
    if seconds is None:
        return
    if seconds < 0 or seconds > episode.duration_seconds:
        raise AppError(
            "CHAPTER_OUT_OF_RANGE",
            422,
            detail=f"{seconds}s 超出单集时长 {episode.duration_seconds}s",
        )


def _assert_unique(db, episode_id: int, seconds: int | None, exclude_id: int | None = None) -> None:
    if seconds is None:
        return
    rows = _chapters(db, episode_id)
    for row in rows:
        if row.id == exclude_id or row.start_seconds is None:
            continue
        if row.start_seconds == seconds:
            raise AppError(
                "CHAPTER_DUPLICATE",
                409,
                detail=f"{to_short_timecode(seconds)} 已存在章节「{row.title}」",
            )


def add_chapter(db, episode_code: str, payload: dict, actor_email: str) -> dict:
    episode, _ = episode_service.get_episode(db, episode_code)
    rows = _chapters(db, episode.id)
    if len(rows) >= MAX_CHAPTERS_PER_EPISODE:
        raise AppError("VALIDATION", 422, detail=f"单集章节上限 {MAX_CHAPTERS_PER_EPISODE}")

    seconds, meta = _resolve_seconds(episode, payload, None)
    if seconds is None:
        raise AppError("VALIDATION", 422, detail="新增章节必须给出 start_seconds 或 raw_text")
    _assert_range(episode, seconds)
    _assert_unique(db, episode.id, seconds)

    chapter = Chapter(
        episode_id=episode.id,
        ordinal=len(rows),
        start_seconds=seconds,
        title=(payload.get("title") or "未命名章节")[:200],
        raw_text=(payload.get("raw_text") or "")[:500],
        parse_rule=meta["rule"] or "manual",
        confidence=1.0,
        ambiguous=meta["ambiguous"],
        source=ChapterSource.MANUAL.value,
    )
    db.add(chapter)
    db.flush()
    _resequence(db, episode.id)
    _refresh(db, episode)
    return {"chapter_id": chapter.id, "open_issues": episode.issue_count}


def update_chapter(db, episode_code: str, chapter_id: int, payload: dict, actor_email: str) -> dict:
    episode, _ = episode_service.get_episode(db, episode_code)
    chapter = db.get(Chapter, chapter_id)
    if chapter is None or chapter.episode_id != episode.id:
        raise AppError("CHAPTER_NOT_FOUND", 404, detail=f"chapter={chapter_id}")

    seconds, meta = _resolve_seconds(episode, payload, chapter.start_seconds)
    _assert_range(episode, seconds)
    _assert_unique(db, episode.id, seconds, exclude_id=chapter.id)

    if payload.get("title") is not None:
        chapter.title = str(payload["title"])[:200] or chapter.title
    if payload.get("raw_text"):
        chapter.raw_text = str(payload["raw_text"])[:500]
    if seconds is not None and seconds != chapter.start_seconds:
        chapter.start_seconds = seconds
    if chapter.start_seconds is not None:
        chapter.source = ChapterSource.MANUAL.value
        chapter.parse_rule = meta["rule"] or "manual"
        chapter.confidence = 1.0
        chapter.ambiguous = False
        chapter.auto_fixed = False
        chapter.fix_note = ""

    db.flush()
    _resequence(db, episode.id)
    _refresh(db, episode)
    return {"chapter_id": chapter.id, "open_issues": episode.issue_count}


def delete_chapter(db, episode_code: str, chapter_id: int, actor_email: str) -> dict:
    episode, _ = episode_service.get_episode(db, episode_code)
    chapter = db.get(Chapter, chapter_id)
    if chapter is None or chapter.episode_id != episode.id:
        raise AppError("CHAPTER_NOT_FOUND", 404, detail=f"chapter={chapter_id}")
    issue_service.purge_for_chapters(db, [chapter.id])
    db.delete(chapter)
    db.flush()
    _resequence(db, episode.id)
    _refresh(db, episode)
    return {"deleted": chapter_id, "open_issues": episode.issue_count}


def _refresh(db, episode) -> None:
    rows = _chapters(db, episode.id)
    episode.chapter_count = len(rows)
    episode.unparsed_count = sum(1 for row in rows if row.start_seconds is None)
    if episode.unparsed_count == 0:
        from src.constants.enums import ParseStatus

        episode.parse_status = ParseStatus.PARSED.value
    else:
        from src.constants.enums import ParseStatus

        episode.parse_status = ParseStatus.PARTIAL.value
    db.flush()
    issue_service.sync_episode_issues(db, episode)

"""剪辑清单导出：整集清单（每集一行）+ 章节切点清单（每章一行）+ 异常清单。"""
from __future__ import annotations

import csv
import io
import pathlib
from datetime import datetime

from sqlalchemy import select

from src.config.settings import settings
from src.constants.enums import ISSUE_KIND_LABELS, IssueStatus
from src.constants.limits import EXPORT_BOM
from src.models.chapter import Chapter
from src.models.chapter_issue import ChapterIssue
from src.models.episode import Episode
from src.models.feed import Feed
from src.utils.timecode import to_short_timecode, to_timecode

CLIP_COLUMNS = [
    "episode_code",
    "feed_code",
    "show_name",
    "title",
    "published_on",
    "duration_s",
    "duration_tc",
    "chapter_count",
    "clip_in_s",
    "clip_out_s",
    "clip_length_s",
    "clip_in_tc",
    "clip_out_tc",
    "chapter_outline",
]

CHAPTER_COLUMNS = [
    "episode_code",
    "ordinal",
    "start_s",
    "end_s",
    "length_s",
    "start_tc",
    "end_tc",
    "title",
    "source",
    "parse_rule",
    "confidence",
    "ambiguous",
]

ISSUE_COLUMNS = [
    "issue_key",
    "episode_code",
    "kind",
    "kind_label",
    "status",
    "window_start_s",
    "window_end_s",
    "message",
    "suggestion",
    "resolved_by",
    "resolution_note",
]


def _episode_rows(db) -> list[tuple[Episode, Feed, list[Chapter]]]:
    rows = db.execute(
        select(Episode, Feed).join(Feed, Feed.id == Episode.feed_id).order_by(Episode.code)
    ).all()
    result: list[tuple[Episode, Feed, list[Chapter]]] = []
    for episode, feed in rows:
        chapters = list(
            db.scalars(
                select(Chapter)
                .where(Chapter.episode_id == episode.id, Chapter.start_seconds.is_not(None))
                .order_by(Chapter.start_seconds)
            )
        )
        result.append((episode, feed, chapters))
    return result


def clip_list_csv(db) -> tuple[str, int]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CLIP_COLUMNS)
    count = 0
    for episode, feed, chapters in _episode_rows(db):
        clip_in = chapters[0].start_seconds if chapters else 0
        clip_out = episode.duration_seconds
        outline = " · ".join(chapter.title for chapter in chapters[:4])
        if len(chapters) > 4:
            outline += " …"
        writer.writerow(
            [
                episode.code,
                feed.code,
                feed.show_name,
                episode.title,
                episode.published_on.isoformat() if episode.published_on else "",
                episode.duration_seconds,
                to_timecode(episode.duration_seconds),
                len(chapters),
                clip_in,
                clip_out,
                max(0, clip_out - clip_in),
                to_timecode(clip_in),
                to_timecode(clip_out),
                outline,
            ]
        )
        count += 1
    return EXPORT_BOM + buffer.getvalue(), count


def chapter_cuts_csv(db) -> tuple[str, int]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CHAPTER_COLUMNS)
    count = 0
    for episode, _feed, chapters in _episode_rows(db):
        for index, chapter in enumerate(chapters):
            start = chapter.start_seconds or 0
            end = chapters[index + 1].start_seconds if index + 1 < len(chapters) else episode.duration_seconds
            writer.writerow(
                [
                    episode.code,
                    chapter.ordinal,
                    start,
                    end,
                    max(0, (end or 0) - start),
                    to_short_timecode(start),
                    to_short_timecode(end),
                    chapter.title,
                    chapter.source,
                    chapter.parse_rule,
                    f"{chapter.confidence:.2f}",
                    "yes" if chapter.ambiguous else "no",
                ]
            )
            count += 1
    return EXPORT_BOM + buffer.getvalue(), count


def issues_csv(db, only_open: bool = False) -> tuple[str, int]:
    stmt = select(ChapterIssue, Episode).join(Episode, Episode.id == ChapterIssue.episode_id)
    if only_open:
        stmt = stmt.where(ChapterIssue.status == IssueStatus.OPEN.value)
    rows = db.execute(stmt.order_by(ChapterIssue.kind, ChapterIssue.id)).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(ISSUE_COLUMNS)
    for issue, episode in rows:
        writer.writerow(
            [
                issue.issue_key,
                episode.code,
                issue.kind,
                ISSUE_KIND_LABELS.get(issue.kind, issue.kind),
                issue.status,
                issue.window_start if issue.window_start is not None else "",
                issue.window_end if issue.window_end is not None else "",
                issue.message,
                issue.suggestion,
                issue.resolved_by,
                issue.resolution_note,
            ]
        )
    return EXPORT_BOM + buffer.getvalue(), len(rows)


def write_artifact(name: str, content: str) -> str:
    """同时落一份到共享卷（backend 与 worker 都挂了 tape_archive），便于事后核对。"""
    directory = pathlib.Path(settings.export_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(content, encoding="utf-8")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (directory / f"{path.stem}-{stamp}{path.suffix}").write_text(content, encoding="utf-8")
    return str(path)

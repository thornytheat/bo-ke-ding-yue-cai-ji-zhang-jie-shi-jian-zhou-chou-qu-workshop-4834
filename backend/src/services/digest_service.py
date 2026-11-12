"""采集 / 解析批次编排：worker 与 backend 内联降级共用同一份实现。

采集（ingest）：
  逐源读确定性夹具 → 按 guid 对单集做 upsert
  · ingest_state=pending 的「水位线后新到达」→ 计为新增并置 synced
  · 内容指纹变化 → 用平台版本覆盖标题/简介/时长/show notes，计为更新
  · 其余 → 不变
解析（parse）：
  逐集重跑时间戳解析（保留人工补录章节）→ 重建 auto 章节 → 跑窗口不变量校验 → 更新异常工单
"""
from __future__ import annotations

import time
from collections import Counter

from sqlalchemy import func, select

from src.constants.enums import (
    ChapterSource,
    IngestState,
    ParseStatus,
    TaskMode,
    TaskStatus,
)
from src.models.chapter import Chapter
from src.models.digest_task import DigestTask
from src.models.episode import Episode
from src.models.feed import Feed
from src.services import fixture_service, issue_service, parse_service, validation_service
from src.utils.fingerprint import episode_fingerprint
from src.utils.logger import get_logger
from src.utils.timecode import to_short_timecode
from src.utils.timeutil import utcnow

logger = get_logger("digest")


def _log(task: DigestTask, text: str, level: str = "info") -> None:
    lines = list(task.log_lines or [])
    lines.append({"level": level, "text": text, "at": utcnow().strftime("%H:%M:%S")})
    task.log_lines = lines


def next_episode_code(db) -> str:
    max_code = db.scalar(select(func.max(Episode.code))) or "EP-000"
    try:
        current = int(str(max_code).split("-")[1])
    except (IndexError, ValueError):  # pragma: no cover
        current = 0
    return f"EP-{current + 1:03d}"


def next_task_code(db) -> str:
    max_code = db.scalar(select(func.max(DigestTask.code))) or "DG-0000"
    try:
        current = int(str(max_code).split("-")[1])
    except (IndexError, ValueError):  # pragma: no cover
        current = 0
    return f"DG-{current + 1:04d}"


def _feeds_in_scope(db, feed_codes: list[str] | None) -> list[Feed]:
    stmt = select(Feed).order_by(Feed.sort_order)
    if feed_codes:
        stmt = stmt.where(Feed.code.in_(feed_codes))
    return list(db.scalars(stmt))


def run_ingest(db, task: DigestTask, feed_codes: list[str] | None = None) -> dict:
    feeds = _feeds_in_scope(db, feed_codes)
    active_feeds = [feed for feed in feeds if feed.active]
    skipped = len(feeds) - len(active_feeds)
    if skipped:
        _log(task, f"{skipped} 个订阅源已停用，跳过", "warn")

    new_count = updated_count = unchanged_count = scanned = 0
    for feed in active_feeds:
        _log(task, f"{feed.code} 读取夹具 {feed.fixture_path}（{feed.kind}）")
        try:
            records = fixture_service.load_feed_records(feed)
        except fixture_service.FixtureError as exc:
            _log(task, f"{feed.code} 夹具解析失败：{exc}", "error")
            feed.last_status = "error"
            continue

        feed_new = feed_updated = 0
        for record in records:
            scanned += 1
            episode = db.scalar(select(Episode).where(Episode.guid == record.guid))
            fingerprint = episode_fingerprint(
                record.title, record.summary, record.duration_seconds, record.show_notes
            )
            if episode is None:
                episode = Episode(
                    code=next_episode_code(db),
                    feed_id=feed.id,
                    guid=record.guid,
                    title=record.title,
                    duration_seconds=record.duration_seconds,
                    published_on=record.published_on,
                    summary=record.summary,
                    show_notes=record.show_notes,
                    ingest_state=IngestState.SYNCED.value,
                    parse_status=ParseStatus.PENDING.value,
                    content_hash=fingerprint,
                )
                db.add(episode)
                db.flush()
                new_count += 1
                feed_new += 1
                continue

            was_pending = episode.ingest_state == IngestState.PENDING.value
            if was_pending:
                episode.ingest_state = IngestState.SYNCED.value
                new_count += 1
                feed_new += 1

            if episode.content_hash != fingerprint:
                notes_changed = (episode.show_notes or "").strip() != record.show_notes.strip()
                episode.title = record.title
                episode.summary = record.summary
                episode.duration_seconds = record.duration_seconds
                episode.published_on = record.published_on
                episode.show_notes = record.show_notes
                episode.content_hash = fingerprint
                if notes_changed:
                    episode.parse_status = ParseStatus.PENDING.value
                updated_count += 1
                feed_updated += 1
                continue

            if not was_pending:
                unchanged_count += 1

        feed.last_fetch_at = utcnow()
        feed.last_status = "ok"
        feed.last_episode_count = len(records)
        _log(
            task,
            f"{feed.code} 命中 {len(records)} 条（新增 {feed_new} / 更新 {feed_updated}）",
        )

    task.feeds_scanned = len(active_feeds)
    task.episodes_scanned = scanned
    task.episodes_new = new_count
    task.episodes_updated = updated_count
    task.episodes_unchanged = max(0, unchanged_count)
    _log(
        task,
        f"采集完成：扫描 {scanned} 集，新增 {new_count}，更新 {updated_count}，不变 {unchanged_count}",
    )
    return {
        "feeds_scanned": len(active_feeds),
        "episodes_scanned": scanned,
        "episodes_new": new_count,
        "episodes_updated": updated_count,
        "episodes_unchanged": unchanged_count,
    }


def rebuild_chapters(db, episode: Episode) -> dict:
    """重跑时间戳解析，重建 auto/unparsed 章节，保留人工补录行。"""
    parsed = parse_service.parse_show_notes(episode.show_notes, episode.duration_seconds)

    manual_rows = list(
        db.scalars(
            select(Chapter)
            .where(Chapter.episode_id == episode.id, Chapter.source == ChapterSource.MANUAL.value)
            .order_by(Chapter.ordinal)
        )
    )
    auto_rows = list(
        db.scalars(
            select(Chapter).where(
                Chapter.episode_id == episode.id,
                Chapter.source != ChapterSource.MANUAL.value,
            )
        )
    )
    if auto_rows:
        issue_service.purge_for_chapters(db, [row.id for row in auto_rows])
    for row in auto_rows:
        db.delete(row)
    db.flush()

    created: list[Chapter] = []
    for entry in parsed.entries:
        source = ChapterSource.PARSE.value if entry.seconds is not None else ChapterSource.UNPARSED.value
        chapter = Chapter(
            episode_id=episode.id,
            ordinal=len(created),
            start_seconds=entry.seconds,
            title=entry.title,
            raw_text=entry.raw,
            parse_rule=entry.rule,
            confidence=entry.confidence,
            ambiguous=entry.ambiguous,
            source=source,
        )
        db.add(chapter)
        created.append(chapter)
    db.flush()

    # 注意：这里保持 show notes 的行序，不做排序。
    # 「乱序」本身就是不变量校验要抓的东西，重解析阶段排序会把问题洗掉。
    # 排序只发生在人工点「应用不变量修正」时（episode_service.normalize_episode）。
    episode.chapter_count = len(created) + len(manual_rows)
    episode.unparsed_count = len(parsed.unparsed)
    if episode.unparsed_count == 0:
        episode.parse_status = ParseStatus.PARSED.value
    elif episode.unparsed_count < episode.chapter_count:
        episode.parse_status = ParseStatus.PARTIAL.value
    else:
        episode.parse_status = ParseStatus.FAILED.value
    episode.parsed_at = utcnow()

    return {
        "entries": len(parsed.entries),
        "unparsed": len(parsed.unparsed),
        "ambiguous": parsed.ambiguous_count,
        "rule_usage": parsed.rule_usage,
        "about_minutes": [
            {"raw": entry.raw, "seconds": entry.seconds}
            for entry in parsed.entries
            if entry.rule == "about_minutes" and entry.seconds is not None
        ],
    }


def run_parse(db, task: DigestTask, feed_codes: list[str] | None = None) -> dict:
    stmt = select(Episode).order_by(Episode.code)
    if feed_codes:
        stmt = stmt.join(Feed, Feed.id == Episode.feed_id).where(Feed.code.in_(feed_codes))
    episodes = list(db.scalars(stmt))

    chapters_total = unparsed_total = 0
    rule_usage: Counter[str] = Counter()
    about_minutes: list[dict] = []
    for episode in episodes:
        stats = rebuild_chapters(db, episode)
        chapters_total += stats["entries"]
        unparsed_total += stats["unparsed"]
        rule_usage.update(stats["rule_usage"])
        for item in stats["about_minutes"]:
            about_minutes.append({"episode": episode.code, **item})

    open_issues = 0
    for episode in episodes:
        open_issues += issue_service.sync_episode_issues(db, episode)

    task.episodes_scanned = len(episodes)
    task.chapters_parsed = chapters_total
    task.unparsed_chapters = unparsed_total
    task.issues_found = open_issues

    _log(task, f"解析 {len(episodes)} 集 / {chapters_total} 行章节")
    _log(task, "时间码规则命中：" + "，".join(f"{rule} {count}" for rule, count in sorted(rule_usage.items())))
    if about_minutes:
        for item in about_minutes:
            _log(
                task,
                f"{item['episode']} 模糊时间码「{item['raw']}」→ {item['seconds']}s "
                f"（{to_short_timecode(item['seconds'])}，置信度低需复核）",
                "warn",
            )
    if unparsed_total:
        _log(task, f"未识别 {unparsed_total} 行，已保留原文进异常队列", "warn")
    _log(task, f"不变量校验后待处理异常 {open_issues} 条")
    return {
        "episodes_scanned": len(episodes),
        "chapters_parsed": chapters_total,
        "unparsed": unparsed_total,
        "issues_found": open_issues,
    }


def execute_task(db, task: DigestTask) -> DigestTask:
    started = time.time()
    task.status = TaskStatus.RUNNING.value
    task.started_at = utcnow()
    _log(task, f"批次 {task.code} 开始，模式 {task.mode}")
    db.commit()
    feed_codes = None if task.feed_scope == "all" else [code for code in task.feed_scope.split(",") if code]
    try:
        if task.mode in (TaskMode.INGEST.value, TaskMode.BOTH.value):
            run_ingest(db, task, feed_codes)
        if task.mode in (TaskMode.PARSE.value, TaskMode.BOTH.value):
            run_parse(db, task, feed_codes)
        task.status = TaskStatus.SUCCESS.value
        _log(task, "批次成功")
    except Exception as exc:  # noqa: BLE001 - 失败要落库给运营看
        db.rollback()
        task = db.scalar(select(DigestTask).where(DigestTask.id == task.id)) or task
        task.status = TaskStatus.FAILED.value
        task.error_text = str(exc)[:500]
        _log(task, f"批次失败：{exc}", "error")
        logger.warning("digest task %s failed: %s", task.code, exc)
    finally:
        task.finished_at = utcnow()
        task.duration_ms = int((time.time() - started) * 1000)
        db.commit()
        db.refresh(task)
    return task

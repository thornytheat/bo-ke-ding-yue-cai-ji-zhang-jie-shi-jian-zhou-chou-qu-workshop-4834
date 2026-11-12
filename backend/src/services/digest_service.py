"""采集 / 解析批次编排：worker 与 backend 内联降级共用同一份实现。

批次原子性（整批一个事务，全部读通才落库）：
  · 采集先把范围内所有源的夹具读进内存，任一源断档即抛 FeedIngestError，
    整批回滚 —— 前面源不会先入库，批次明确失败并在 error_text / 日志里指出来源；
  · 所有源读通后才统一 upsert，批次结束一次性 commit，对外只见整批结果；
  · 失败后重试从零开始，不留半批数据；内容指纹不变则不新增、不重复更新。

采集（ingest）：
  逐源读确定性夹具 → 按 guid 对单集做 upsert
  · ingest_state=pending 的「水位线后新到达」→ 计为新增并置 synced
  · 内容指纹变化 → 用平台版本覆盖标题/简介/时长/show notes，计为更新
  · 简介（show notes）变化的集 → 同事务内重建章节时间轴并刷新异常队列
  · 其余 → 不变
解析（parse）：
  逐集重跑时间戳解析（保留人工补录章节）→ 按行序 upsert auto 章节（行 id 稳定，
  工单 issue_key 随之稳定，重复运行零变更）→ 跑窗口不变量校验 → 更新异常工单
"""
from __future__ import annotations

import time
from collections import Counter

from sqlalchemy import func, select

from src.constants.enums import (
    ChapterSource,
    IngestState,
    IssueStatus,
    ParseStatus,
    TaskMode,
    TaskStatus,
)
from src.models.chapter import Chapter
from src.models.chapter_issue import ChapterIssue
from src.models.digest_task import DigestTask
from src.models.episode import Episode
from src.models.feed import Feed
from src.services import fixture_service, issue_service, parse_service, validation_service
from src.utils.fingerprint import episode_fingerprint
from src.utils.logger import get_logger
from src.utils.timecode import to_short_timecode
from src.utils.timeutil import utcnow

logger = get_logger("digest")

# 事务外日志缓冲：业务日志随事务写 task.log_lines，同时收进内存列表；
# 批次失败回滚后由 execute_task 把缓冲写回，失败轨迹（读到哪个源、卡在哪）不丢。
LogCollector = list[dict]


class FeedIngestError(RuntimeError):
    """某个订阅源读取/解析失败：批次整体失败并回滚，错误信息指明来源。"""

    def __init__(self, feed_code: str, detail: str):
        super().__init__(f"订阅源 {feed_code} 读取失败：{detail}")
        self.feed_code = feed_code
        self.detail = detail


def _log(task: DigestTask, text: str, level: str = "info", collector: LogCollector | None = None) -> None:
    line = {"level": level, "text": text, "at": utcnow().strftime("%H:%M:%S")}
    lines = list(task.log_lines or [])
    lines.append(line)
    task.log_lines = lines
    if collector is not None:
        collector.append(line)


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


def _open_issue_total(db) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(ChapterIssue)
            .where(ChapterIssue.status == IssueStatus.OPEN.value)
        )
        or 0
    )


def run_ingest(
    db,
    task: DigestTask,
    feed_codes: list[str] | None = None,
    collector: LogCollector | None = None,
) -> dict:
    feeds = _feeds_in_scope(db, feed_codes)
    active_feeds = [feed for feed in feeds if feed.active]
    skipped = len(feeds) - len(active_feeds)
    if skipped:
        _log(task, f"{skipped} 个订阅源已停用，跳过", "warn", collector)

    # ---- 阶段 1：把所有源的夹具读通（纯 IO，不落库） ----
    # 任一源断档直接抛 FeedIngestError：此时还没写任何业务数据，
    # 整批回滚后数据库保持批次前状态，重试不会对着半批数据核对计数。
    payloads: list[tuple[Feed, list]] = []
    for feed in active_feeds:
        _log(task, f"{feed.code} 读取夹具 {feed.fixture_path}（{feed.kind}）", collector=collector)
        try:
            records = fixture_service.load_feed_records(feed)
        except fixture_service.FixtureError as exc:
            _log(task, f"{feed.code} 夹具解析失败：{exc}", "error", collector)
            raise FeedIngestError(feed.code, str(exc)) from exc
        payloads.append((feed, records))

    # ---- 阶段 2：全部读通后才统一写库（同一事务，批次结束一次性提交） ----
    new_count = updated_count = unchanged_count = scanned = 0
    refreshed: list[Episode] = []
    for feed, records in payloads:
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
                    # 简介变了：章节时间轴与异常队列必须跟着刷新，
                    # 同一事务内重建，批次提交时新旧口径一起对外可见。
                    refreshed.append(episode)
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
            collector=collector,
        )

    # ---- 阶段 3：简介变化的集，章节时间轴 + 异常队列同步刷新（人工补录行不动） ----
    if refreshed:
        for episode in refreshed:
            stats = rebuild_chapters(db, episode)
            issue_service.sync_episode_issues(db, episode)
            _log(
                task,
                f"{episode.code} 简介变更，章节时间轴已刷新"
                f"（{stats['entries']} 行，未识别 {stats['unparsed']}）",
                "warn" if stats["unparsed"] else "info",
                collector,
            )
        task.issues_found = _open_issue_total(db)

    task.feeds_scanned = len(active_feeds)
    task.episodes_scanned = scanned
    task.episodes_new = new_count
    task.episodes_updated = updated_count
    task.episodes_unchanged = max(0, unchanged_count)
    _log(
        task,
        f"采集完成：扫描 {scanned} 集，新增 {new_count}，更新 {updated_count}，不变 {unchanged_count}",
        collector=collector,
    )
    return {
        "feeds_scanned": len(active_feeds),
        "episodes_scanned": scanned,
        "episodes_new": new_count,
        "episodes_updated": updated_count,
        "episodes_unchanged": unchanged_count,
        "episodes_refreshed": len(refreshed),
    }


def rebuild_chapters(db, episode: Episode) -> dict:
    """重跑时间戳解析，按行序 upsert auto/unparsed 章节，人工补录行原样保留。

    不删除重建：行 id 稳定 → 工单 issue_key 稳定 → 重复运行零变更，
    人工处置（resolved）的工单不会被误清；只有行数多出来的尾巴行才删除。
    """
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
            select(Chapter)
            .where(
                Chapter.episode_id == episode.id,
                Chapter.source != ChapterSource.MANUAL.value,
            )
            .order_by(Chapter.ordinal, Chapter.id)
        )
    )

    kept_ids: set[int] = set()
    for index, entry in enumerate(parsed.entries):
        source = ChapterSource.PARSE.value if entry.seconds is not None else ChapterSource.UNPARSED.value
        if index < len(auto_rows):
            row = auto_rows[index]
            content_changed = (
                row.start_seconds != entry.seconds
                or row.title != entry.title
                or (row.raw_text or "") != entry.raw
                or row.source != source
            )
            row.ordinal = index
            row.start_seconds = entry.seconds
            row.title = entry.title
            row.raw_text = entry.raw
            row.parse_rule = entry.rule
            row.confidence = entry.confidence
            row.ambiguous = entry.ambiguous
            row.source = source
            if content_changed:
                # 平台原文覆盖了这一行，旧的「应用不变量修正」标记随之失效
                row.auto_fixed = False
                row.fix_note = ""
            kept_ids.add(row.id)
            continue
        row = Chapter(
            episode_id=episode.id,
            ordinal=index,
            start_seconds=entry.seconds,
            title=entry.title,
            raw_text=entry.raw,
            parse_rule=entry.rule,
            confidence=entry.confidence,
            ambiguous=entry.ambiguous,
            source=source,
        )
        db.add(row)
        db.flush()
        kept_ids.add(row.id)

    # 行数比上次少：多出来的尾巴行删除，引用它们的工单先清掉避免外键阻塞
    stale = [row for row in auto_rows if row.id not in kept_ids]
    if stale:
        issue_service.purge_for_chapters(db, [row.id for row in stale])
        for row in stale:
            db.delete(row)
    db.flush()

    # 注意：这里保持 show notes 的行序，不做排序。
    # 「乱序」本身就是不变量校验要抓的东西，重解析阶段排序会把问题洗掉。
    # 排序只发生在人工点「应用不变量修正」时（episode_service.normalize_episode）。
    episode.chapter_count = len(parsed.entries) + len(manual_rows)
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


def run_parse(
    db,
    task: DigestTask,
    feed_codes: list[str] | None = None,
    collector: LogCollector | None = None,
) -> dict:
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

    _log(task, f"解析 {len(episodes)} 集 / {chapters_total} 行章节", collector=collector)
    _log(
        task,
        "时间码规则命中：" + "，".join(f"{rule} {count}" for rule, count in sorted(rule_usage.items())),
        collector=collector,
    )
    if about_minutes:
        for item in about_minutes:
            _log(
                task,
                f"{item['episode']} 模糊时间码「{item['raw']}」→ {item['seconds']}s "
                f"（{to_short_timecode(item['seconds'])}，置信度低需复核）",
                "warn",
                collector,
            )
    if unparsed_total:
        _log(task, f"未识别 {unparsed_total} 行，已保留原文进异常队列", "warn", collector)
    _log(task, f"不变量校验后待处理异常 {open_issues} 条", collector=collector)
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
    collector: LogCollector = []
    try:
        if task.mode in (TaskMode.INGEST.value, TaskMode.BOTH.value):
            run_ingest(db, task, feed_codes, collector)
        if task.mode in (TaskMode.PARSE.value, TaskMode.BOTH.value):
            run_parse(db, task, feed_codes, collector)
        task.status = TaskStatus.SUCCESS.value
        _log(task, "批次成功")
    except Exception as exc:  # noqa: BLE001 - 失败要落库给运营看
        # 整批回滚：不留半批数据，重试从零开始
        db.rollback()
        task = db.get(DigestTask, task.id) or task
        task.status = TaskStatus.FAILED.value
        task.error_text = str(exc)[:500]
        # 回滚会丢掉事务内累积的日志，用内存缓冲把处理轨迹补回来
        task.log_lines = [*(task.log_lines or []), *collector]
        _log(task, f"批次失败：{exc}", "error")
        if isinstance(exc, FeedIngestError):
            # 指出来源：出错源在源清单上标红，运营能直接定位
            feed = db.scalar(select(Feed).where(Feed.code == exc.feed_code))
            if feed is not None:
                feed.last_status = "error"
        logger.warning("digest task %s failed: %s", task.code, exc)
    finally:
        task.finished_at = utcnow()
        task.duration_ms = int((time.time() - started) * 1000)
        db.commit()
        db.refresh(task)
    return task

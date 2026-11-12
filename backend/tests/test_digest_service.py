"""采集/解析批次的服务层契约测试（SQLite 内存库，不碰 MySQL / Celery）。

锁定的行为：
  · 一批采集在所有源都读通后才统一可见：任一源断档 → 整批回滚，
    前面源不会先入库，批次 FAILED 并在 error_text / 日志里指出来源；
  · 失败后重试不留半批数据，计数与「首次全量成功」一致；
  · 重复运行同一批：不新增、不重复更新，章节行 id 与异常工单保持稳定；
  · 简介（show notes）变化 → 章节时间轴与异常队列在采集批次内跟着刷新，
    人工补录的章节保持原样。
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.config.settings import settings
from src.constants.enums import ChapterSource, IssueStatus, ParseStatus, TaskMode, TaskStatus
from src.models import Base
from src.models.chapter import Chapter
from src.models.chapter_issue import ChapterIssue
from src.models.digest_task import DigestTask
from src.models.episode import Episode
from src.models.feed import Feed
from src.services import digest_service, issue_service

# ---------------------------------------------------------------- 测试基建


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """SQLite 内存库 + 独立夹具目录。"""
    monkeypatch.setattr(settings, "fixture_dir", str(tmp_path))
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as session:
        yield session
    engine.dispose()


def _rss(items: list[dict]) -> str:
    rows = []
    for item in items:
        rows.append(
            "\n".join(
                [
                    "    <item>",
                    f"      <title>{item['title']}</title>",
                    f'      <guid isPermaLink="false">{item["guid"]}</guid>',
                    "      <pubDate>Wed, 16 Sep 2026 09:00:00 +0800</pubDate>",
                    f"      <itunes:duration>{item['duration']}</itunes:duration>",
                    f"      <itunes:summary><![CDATA[{item['summary']}]]></itunes:summary>",
                    f"      <description><![CDATA[{item['notes']}]]></description>",
                    "    </item>",
                ]
            )
        )
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">',
            "  <channel>",
            "    <title>测试节目</title>",
            *rows,
            "  </channel>",
            "</rss>",
            "",
        ]
    )


def _write_fixture(tmp_path, name: str, content: str) -> None:
    (tmp_path / name).write_text(content, encoding="utf-8")


def _add_feed(db, code: str, fixture: str, sort: int) -> Feed:
    feed = Feed(
        code=code,
        name=f"节目 {code}",
        show_name=f"show-{code}",
        kind="rss",
        url=f"https://feeds.test/{code}.xml",
        fixture_path=fixture,
        sort_order=sort,
        active=True,
        last_status="never",
    )
    db.add(feed)
    db.flush()
    return feed


def _new_task(db, mode: str = TaskMode.INGEST.value, scope: str = "all") -> DigestTask:
    task = DigestTask(
        code=digest_service.next_task_code(db),
        mode=mode,
        status=TaskStatus.QUEUED.value,
        feed_scope=scope,
        triggered_by="tester@podcastdig.io",
        triggered_role="admin",
        log_lines=[],
    )
    db.add(task)
    db.commit()
    return task


def _episode_count(db) -> int:
    return db.scalar(select(func.count()).select_from(Episode)) or 0


def _chapters_of(db, episode_id: int) -> list[Chapter]:
    return list(
        db.scalars(
            select(Chapter)
            .where(Chapter.episode_id == episode_id)
            .order_by(Chapter.ordinal, Chapter.id)
        )
    )


def _issues_of(db, episode_id: int) -> list[ChapterIssue]:
    return list(db.scalars(select(ChapterIssue).where(ChapterIssue.episode_id == episode_id)))


NOTES_V1 = "00:30 开场白\n05:00 第一段话题\n12:30 第二段话题"
NOTES_V2 = "00:30 开场白\n05:00 第一段话题\n12:30 第二段话题\n25:00 新增收尾段\n45:00 越界的一行"


def _items(prefix: str, count: int, notes: str = NOTES_V1) -> list[dict]:
    return [
        {
            "guid": f"test:{prefix}:{index}",
            "title": f"{prefix} 第 {index} 集",
            "duration": "00:31:20",
            "summary": f"{prefix} 第 {index} 集简介",
            "notes": notes,
        }
        for index in range(1, count + 1)
    ]


# ---------------------------------------------------------------- 原子性


def test_broken_feed_fails_whole_batch_atomically(db, tmp_path):
    """六源里只要一个断档：整批回滚，前面源不入库，批次 FAILED 并指出来源。"""
    _write_fixture(tmp_path, "alpha.xml", _rss(_items("alpha", 2)))
    _write_fixture(tmp_path, "omega.xml", _rss(_items("omega", 2)))
    # broken.xml 根本不存在 → FixtureError
    alpha = _add_feed(db, "alpha", "alpha.xml", 1)
    broken = _add_feed(db, "broken", "broken.xml", 2)
    omega = _add_feed(db, "omega", "omega.xml", 3)

    task = digest_service.execute_task(db, _new_task(db))

    assert task.status == TaskStatus.FAILED.value
    assert "broken" in task.error_text
    # 前面读通的源也没有先入库：整批不可见
    assert _episode_count(db) == 0
    db.refresh(alpha)
    db.refresh(omega)
    db.refresh(broken)
    assert alpha.last_status == "never"
    assert omega.last_status == "never"
    # 出错 的源被点名标红
    assert broken.last_status == "error"
    log_text = "\n".join(line["text"] for line in task.log_lines)
    assert "broken" in log_text
    assert "批次失败" in log_text


def test_failed_batch_preserves_previous_data(db, tmp_path):
    """已有数据 + 重跑失败：旧数据原样保留，不留半批更新。"""
    _write_fixture(tmp_path, "alpha.xml", _rss(_items("alpha", 1)))
    _write_fixture(tmp_path, "omega.xml", _rss(_items("omega", 1)))
    _add_feed(db, "alpha", "alpha.xml", 1)
    _add_feed(db, "omega", "omega.xml", 2)
    first = digest_service.execute_task(db, _new_task(db))
    assert first.status == TaskStatus.SUCCESS.value
    hash_before = db.scalar(select(Episode.content_hash).where(Episode.guid == "test:alpha:1"))

    # alpha 内容升级（简介变化），omega 断档 → 整批必须失败且 alpha 的更新不落库
    changed = _items("alpha", 1)
    changed[0]["summary"] = "alpha 第 1 集简介（平台修订版）"
    _write_fixture(tmp_path, "alpha.xml", _rss(changed))
    (tmp_path / "omega.xml").write_text("<rss><channel><item>", encoding="utf-8")

    task = digest_service.execute_task(db, _new_task(db))

    assert task.status == TaskStatus.FAILED.value
    assert "omega" in task.error_text
    assert db.scalar(select(Episode.content_hash).where(Episode.guid == "test:alpha:1")) == hash_before
    assert db.scalar(select(Episode.summary).where(Episode.guid == "test:alpha:1")) == "alpha 第 1 集简介"


def test_retry_after_fix_counts_like_first_full_run(db, tmp_path):
    """修复断档源后重试：不留半批，新增/更新计数与首次全量成功一致。"""
    _write_fixture(tmp_path, "alpha.xml", _rss(_items("alpha", 2)))
    _add_feed(db, "alpha", "alpha.xml", 1)
    _add_feed(db, "broken", "broken.xml", 2)

    failed = digest_service.execute_task(db, _new_task(db))
    assert failed.status == TaskStatus.FAILED.value
    assert _episode_count(db) == 0

    _write_fixture(tmp_path, "broken.xml", _rss(_items("broken", 3)))
    retried = digest_service.execute_task(db, _new_task(db))

    assert retried.status == TaskStatus.SUCCESS.value
    assert retried.episodes_scanned == 5
    assert retried.episodes_new == 5  # 首次全量入库：5 集全部计新增
    assert retried.episodes_updated == 0
    assert _episode_count(db) == 5


# ---------------------------------------------------------------- 幂等


def test_rerun_is_idempotent_for_episodes_chapters_and_issues(db, tmp_path):
    """重复运行同一批：不新增、不重复更新；章节行 id 与工单保持稳定。"""
    notes = NOTES_V1 + "\n1:2345 行首像时间码但解析不了"
    _write_fixture(tmp_path, "alpha.xml", _rss(_items("alpha", 2, notes)))
    _add_feed(db, "alpha", "alpha.xml", 1)

    first = digest_service.execute_task(db, _new_task(db, mode=TaskMode.BOTH.value))
    assert first.status == TaskStatus.SUCCESS.value
    assert first.issues_found > 0  # 每集 1 行未识别 → 有工单

    chapter_ids_before = {
        row.id for row in db.scalars(select(Chapter))
    }
    issue_keys_before = {
        row.issue_key: row.status for row in db.scalars(select(ChapterIssue))
    }

    # 人工处置一条工单，重跑不能让它复活或消失
    some_issue = db.scalar(select(ChapterIssue).limit(1))
    issue_service.resolve_issue(db, some_issue.id, "人工确认无误", "analyst@podcastdig.io")
    db.commit()

    second = digest_service.execute_task(db, _new_task(db, mode=TaskMode.BOTH.value))

    assert second.status == TaskStatus.SUCCESS.value
    assert second.episodes_new == 0
    assert second.episodes_updated == 0
    assert second.episodes_unchanged == 2
    # 章节行 id 完全稳定（upsert 而非删除重建）
    assert {row.id for row in db.scalars(select(Chapter))} == chapter_ids_before
    # 工单不新增、不复活、不丢
    issues_after = {row.issue_key: row.status for row in db.scalars(select(ChapterIssue))}
    assert set(issues_after) == set(issue_keys_before)
    assert issues_after[some_issue.issue_key] == IssueStatus.RESOLVED.value
    assert second.issues_found == sum(1 for s in issues_after.values() if s == IssueStatus.OPEN.value)


# ---------------------------------------------------------------- 简介变更刷新


def test_summary_change_refreshes_timeline_and_issues_in_ingest_batch(db, tmp_path):
    """简介变化后：采集批次内章节时间轴与异常队列跟着刷新（不必等解析批次）。"""
    _write_fixture(tmp_path, "alpha.xml", _rss(_items("alpha", 1)))
    _add_feed(db, "alpha", "alpha.xml", 1)
    first = digest_service.execute_task(db, _new_task(db, mode=TaskMode.BOTH.value))
    assert first.status == TaskStatus.SUCCESS.value

    episode = db.scalar(select(Episode).where(Episode.guid == "test:alpha:1"))
    assert episode.chapter_count == 3
    assert _issues_of(db, episode.id) == []

    # 平台改简介：多两章，其中一行时间点超出时长（45:00 > 31:20）
    changed = _items("alpha", 1, NOTES_V2)
    changed[0]["summary"] = "alpha 第 1 集简介（平台修订版）"
    _write_fixture(tmp_path, "alpha.xml", _rss(changed))

    ingest = digest_service.execute_task(db, _new_task(db, mode=TaskMode.INGEST.value))

    assert ingest.status == TaskStatus.SUCCESS.value
    assert ingest.episodes_updated == 1
    db.refresh(episode)
    # 采集批次提交时章节时间轴已是新版
    assert episode.chapter_count == 5
    assert episode.parse_status == ParseStatus.PARSED.value
    titles = [row.title for row in _chapters_of(db, episode.id)]
    assert "新增收尾段" in titles
    # 异常队列同步刷新：超时长工单出现
    kinds = {row.kind for row in _issues_of(db, episode.id)}
    assert "over_duration" in kinds
    assert episode.issue_count == len(_issues_of(db, episode.id))
    assert ingest.issues_found == episode.issue_count


def test_shrinking_notes_only_drops_tail_rows(db, tmp_path):
    """简介行数变少：多余尾巴行删除（其工单清掉），其余行 id 稳定。"""
    _write_fixture(tmp_path, "alpha.xml", _rss(_items("alpha", 1, NOTES_V2)))
    _add_feed(db, "alpha", "alpha.xml", 1)
    digest_service.execute_task(db, _new_task(db, mode=TaskMode.BOTH.value))

    episode = db.scalar(select(Episode).where(Episode.guid == "test:alpha:1"))
    assert episode.chapter_count == 5
    ids_before = [row.id for row in _chapters_of(db, episode.id)]
    # 超时长行本身有一条例外工单，删除后应随之清掉
    assert db.scalar(
        select(func.count()).select_from(ChapterIssue).where(ChapterIssue.kind == "over_duration")
    ) == 1

    # 平台把简介改回 3 行版本
    _write_fixture(tmp_path, "alpha.xml", _rss(_items("alpha", 1, NOTES_V1)))
    ingest = digest_service.execute_task(db, _new_task(db, mode=TaskMode.INGEST.value))
    assert ingest.status == TaskStatus.SUCCESS.value

    db.refresh(episode)
    assert episode.chapter_count == 3
    ids_after = [row.id for row in _chapters_of(db, episode.id)]
    # 前 3 行 id 稳定，尾巴 2 行被删
    assert ids_after == ids_before[:3]
    assert db.scalar(
        select(func.count()).select_from(ChapterIssue).where(ChapterIssue.kind == "over_duration")
    ) == 0


def test_manual_chapters_survive_ingest_refresh(db, tmp_path):
    """简介变化触发重建时，人工补录的章节保持原样。"""
    _write_fixture(tmp_path, "alpha.xml", _rss(_items("alpha", 1)))
    _add_feed(db, "alpha", "alpha.xml", 1)
    digest_service.execute_task(db, _new_task(db, mode=TaskMode.BOTH.value))

    episode = db.scalar(select(Episode).where(Episode.guid == "test:alpha:1"))
    manual = Chapter(
        episode_id=episode.id,
        ordinal=99,
        start_seconds=777,
        title="人工补录的彩蛋段",
        raw_text="12:57 彩蛋",
        parse_rule="manual",
        confidence=1.0,
        source=ChapterSource.MANUAL.value,
    )
    db.add(manual)
    db.commit()
    manual_id = manual.id

    changed = _items("alpha", 1, NOTES_V2)
    _write_fixture(tmp_path, "alpha.xml", _rss(changed))
    ingest = digest_service.execute_task(db, _new_task(db, mode=TaskMode.INGEST.value))
    assert ingest.status == TaskStatus.SUCCESS.value

    db.refresh(episode)
    kept = db.get(Chapter, manual_id)
    assert kept is not None
    assert kept.title == "人工补录的彩蛋段"
    assert kept.start_seconds == 777
    assert kept.source == ChapterSource.MANUAL.value
    # auto 行已按新简介重建，人工行不计入解析行数但计入总数
    auto_rows = [
        row for row in _chapters_of(db, episode.id) if row.source != ChapterSource.MANUAL.value
    ]
    assert len(auto_rows) == 5
    assert episode.chapter_count == 5 + 1

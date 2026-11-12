"""幂等 seed：3 账号 / 6 订阅源 / 48 单集 / 260 章节 / 22 异常工单 / 4 历史批次。

自然键 upsert：
  users.email
  feeds.code
  episodes.guid
  chapters(episode_id) —— 仅当该集还没有任何章节时按 show notes 真解析生成
  chapter_issues.issue_key —— 只补缺失，不覆盖人工处置结果
  digest_tasks.code / audit_logs.seed_key

章节与异常不是手写常量：seed 调用生产同款 parse_service / validation_service，
所以 SEED_SUMMARY 里的 chapters/issues 就是算法跑出来的真实数字。
重复执行不新增、不覆盖用户修改。
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from src.config.database import session_scope
from src.constants.enums import (
    ChapterSource,
    IngestState,
    ParseStatus,
    TaskStatus,
)
from src.models.audit import AuditLog
from src.models.chapter import Chapter
from src.models.chapter_issue import ChapterIssue
from src.models.digest_task import DigestTask
from src.models.episode import Episode
from src.models.feed import Feed
from src.models.user import User
from src.services import validation_service
from src.services.parse_service import parse_show_notes
from src.utils.fingerprint import episode_fingerprint
from src.utils.logger import get_logger
from src.utils.security import hash_password
from src.utils.timeutil import utcnow
from scripts.demo_config import (
    DEMO_PASSWORD,
    DEMO_USERS,
    EPISODE_BY_CODE,
    EPISODES,
    FEEDS,
    SEED_AUDIT,
    SEED_TASKS,
)

logger = get_logger("seed")


def ensure_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for email, display_name, role in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=display_name,
                role=role,
            )
            db.add(user)
            db.flush()
        users[email] = user
    return users


def ensure_feeds(db) -> dict[str, Feed]:
    feeds: dict[str, Feed] = {}
    for index, spec in enumerate(FEEDS):
        feed = db.scalar(select(Feed).where(Feed.code == spec.code))
        if feed is None:
            feed = Feed(
                code=spec.code,
                name=spec.name,
                show_name=spec.show_name,
                kind=spec.kind,
                url=spec.url,
                fixture_path=spec.fixture_file,
                cadence=spec.cadence,
                host=spec.host,
                note=spec.note,
                sort_order=index,
                active=True,
                last_status="never",
            )
            db.add(feed)
            db.flush()
        feeds[spec.code] = feed
    return feeds


def ensure_episodes(db, feeds: dict[str, Feed]) -> tuple[dict[str, Episode], int]:
    episodes: dict[str, Episode] = {}
    created_chapters = 0
    for spec in EPISODES:
        feed = feeds[spec.feed_code]
        episode = db.scalar(select(Episode).where(Episode.guid == spec.guid))
        if episode is None:
            episode = Episode(
                code=spec.code,
                feed_id=feed.id,
                guid=spec.guid,
                title=spec.title,
                duration_seconds=spec.duration_seconds,
                published_on=spec.published_on,
                summary=spec.summary,
                show_notes=spec.show_notes,
                cover_hint=spec.cover_hint,
                season=spec.season,
                episode_no=spec.episode_no,
                ingest_state=spec.ingest_state,
                parse_status=ParseStatus.PENDING.value,
                content_hash=episode_fingerprint(
                    spec.title, spec.summary, spec.duration_seconds, spec.show_notes
                ),
            )
            db.add(episode)
            db.flush()
        episodes[spec.code] = episode

        existing = db.scalar(
            select(func.count()).select_from(Chapter).where(Chapter.episode_id == episode.id)
        ) or 0
        if existing == 0:
            created_chapters += _seed_chapters(db, episode, spec.show_notes)
    return episodes, created_chapters


def _seed_chapters(db, episode: Episode, show_notes: str) -> int:
    parsed = parse_show_notes(show_notes, episode.duration_seconds)
    created = 0
    for index, entry in enumerate(parsed.entries):
        db.add(
            Chapter(
                episode_id=episode.id,
                ordinal=index,
                start_seconds=entry.seconds,
                title=entry.title,
                raw_text=entry.raw,
                parse_rule=entry.rule,
                confidence=entry.confidence,
                ambiguous=entry.ambiguous,
                source=ChapterSource.PARSE.value if entry.seconds is not None else ChapterSource.UNPARSED.value,
                seed_key=f"seed:chapter:{episode.code}:{index}",
            )
        )
        created += 1
    episode.chapter_count = len(parsed.entries)
    episode.unparsed_count = len(parsed.unparsed)
    if episode.unparsed_count == 0:
        episode.parse_status = ParseStatus.PARSED.value
    elif episode.unparsed_count < episode.chapter_count:
        episode.parse_status = ParseStatus.PARTIAL.value
    else:
        episode.parse_status = ParseStatus.FAILED.value
    episode.parsed_at = utcnow()
    db.flush()
    return created


def ensure_issues(db, episodes: dict[str, Episode], force: bool, created_chapters: int) -> int:
    """按生产校验器生成工单，只补缺失的 issue_key。"""
    issue_total = db.scalar(select(func.count()).select_from(ChapterIssue)) or 0
    if not force and issue_total > 0 and created_chapters == 0:
        return issue_total

    for episode in episodes.values():
        chapters = list(
            db.scalars(select(Chapter).where(Chapter.episode_id == episode.id).order_by(Chapter.ordinal))
        )
        if not chapters:
            continue
        result = validation_service.validate_episode(
            episode.code,
            episode.duration_seconds,
            validation_service.chapter_inputs(chapters),
        )
        existing = {
            row.issue_key: row
            for row in db.scalars(select(ChapterIssue).where(ChapterIssue.episode_id == episode.id))
        }
        for draft in result.issues:
            if draft.issue_key in existing:
                continue
            db.add(
                ChapterIssue(
                    issue_key=draft.issue_key,
                    episode_id=episode.id,
                    chapter_id=draft.chapter_id,
                    kind=draft.kind,
                    status="open",
                    severity=draft.severity,
                    message=draft.message,
                    suggestion=draft.suggestion,
                    window_start=draft.window_start,
                    window_end=draft.window_end,
                    detected_by="validator",
                    seed_key=f"seed:issue:{draft.issue_key}",
                )
            )
        db.flush()
        episode.issue_count = (
            db.scalar(
                select(func.count())
                .select_from(ChapterIssue)
                .where(ChapterIssue.episode_id == episode.id, ChapterIssue.status == "open")
            )
            or 0
        )

    db.flush()
    return db.scalar(select(func.count()).select_from(ChapterIssue)) or 0


def ensure_tasks(db) -> int:
    now = utcnow()
    for spec in SEED_TASKS:
        exists = db.scalar(select(DigestTask).where(DigestTask.code == spec["code"]))
        if exists is not None:
            continue
        started = now - timedelta(minutes=spec["started_ago_minutes"])
        finished = started + timedelta(milliseconds=spec["duration_ms"])
        db.add(
            DigestTask(
                code=spec["code"],
                mode=spec["mode"],
                status=spec["status"],
                feed_scope=spec["feed_scope"],
                triggered_by=spec["triggered_by"],
                triggered_role=spec["triggered_role"],
                feeds_scanned=spec["feeds_scanned"],
                episodes_scanned=spec["episodes_scanned"],
                episodes_new=spec["episodes_new"],
                episodes_updated=spec["episodes_updated"],
                episodes_unchanged=spec["episodes_unchanged"],
                chapters_parsed=spec["chapters_parsed"],
                unparsed_chapters=spec["unparsed_chapters"],
                issues_found=spec["issues_found"],
                duration_ms=spec["duration_ms"],
                log_lines=[
                    {"level": "error" if spec["status"] == TaskStatus.FAILED.value else "info", "text": line}
                    for line in spec["log_lines"]
                ],
                error_text=spec.get("error_text", ""),
                started_at=started,
                finished_at=finished,
                seed_key=f"seed:task:{spec['code']}",
                created_at=started,
            )
        )
    db.flush()
    return db.scalar(select(func.count()).select_from(DigestTask)) or 0


def ensure_audit(db) -> None:
    for seed_key, email, role, action, entity, entity_id, detail in SEED_AUDIT:
        if db.scalar(select(AuditLog).where(AuditLog.seed_key == seed_key)):
            continue
        db.add(
            AuditLog(
                actor_email=email,
                actor_role=role,
                action=action,
                entity=entity,
                entity_id=entity_id,
                detail=detail,
                layer="seed",
                ip="127.0.0.1",
                seed_key=seed_key,
            )
        )
    db.flush()


def seed_all() -> str:
    with session_scope() as db:
        users = ensure_users(db)
        feeds = ensure_feeds(db)
        episodes, created_chapters = ensure_episodes(db, feeds)
        issue_total = ensure_issues(db, episodes, force=False, created_chapters=created_chapters)
        ensure_tasks(db)
        ensure_audit(db)

        feed_count = db.scalar(select(func.count()).select_from(Feed)) or 0
        episode_count = db.scalar(select(func.count()).select_from(Episode)) or 0
        chapter_count = db.scalar(select(func.count()).select_from(Chapter)) or 0
        user_count = db.scalar(select(func.count()).select_from(User)) or 0
        issue_total = db.scalar(select(func.count()).select_from(ChapterIssue)) or 0

    summary = (
        f"SEED_SUMMARY brand=podcastdig feeds={feed_count} episodes={episode_count} "
        f"chapters={chapter_count} issues={issue_total} users={user_count}"
    )
    logger.info("seed done, users=%s feeds=%s episodes=%s", user_count, feed_count, episode_count)
    print(summary, flush=True)
    return summary


if __name__ == "__main__":
    seed_all()

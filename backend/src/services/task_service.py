"""采集/解析批次服务：建单、投递 worker（失败则内联降级）、列表与详情。"""
from __future__ import annotations

from sqlalchemy import func, select

from src.config.celery_app import TASK_RUN_DIGEST, celery_app
from src.config.database import SessionLocal
from src.constants.enums import (
    TASK_MODE_LABELS,
    TASK_STATUS_LABELS,
    TaskMode,
    TaskStatus,
)
from src.models.digest_task import DigestTask
from src.models.feed import Feed
from src.services import digest_service
from src.utils.errors import AppError
from src.utils.logger import get_logger
from src.utils.timeutil import local_iso

logger = get_logger("task_service")


def task_to_dict(task: DigestTask) -> dict:
    return {
        "id": task.id,
        "code": task.code,
        "mode": task.mode,
        "mode_label": TASK_MODE_LABELS.get(task.mode, task.mode),
        "status": task.status,
        "status_label": TASK_STATUS_LABELS.get(task.status, task.status),
        "feed_scope": task.feed_scope,
        "triggered_by": task.triggered_by,
        "triggered_role": task.triggered_role,
        "feeds_scanned": task.feeds_scanned,
        "episodes_scanned": task.episodes_scanned,
        "episodes_new": task.episodes_new,
        "episodes_updated": task.episodes_updated,
        "episodes_unchanged": task.episodes_unchanged,
        "chapters_parsed": task.chapters_parsed,
        "unparsed_chapters": task.unparsed_chapters,
        "issues_found": task.issues_found,
        "duration_ms": task.duration_ms,
        "log_lines": task.log_lines or [],
        "error_text": task.error_text,
        "started_at": local_iso(task.started_at),
        "finished_at": local_iso(task.finished_at),
        "created_at": local_iso(task.created_at),
    }


def list_tasks(db, limit: int = 30) -> list[dict]:
    rows = db.scalars(select(DigestTask).order_by(DigestTask.id.desc()).limit(limit))
    return [task_to_dict(task) for task in rows]


def get_task(db, code: str) -> DigestTask:
    task = db.scalar(select(DigestTask).where(DigestTask.code == code))
    if task is None:
        raise AppError("NOT_FOUND", 404, detail=f"task={code}")
    return task


def running_count(db) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(DigestTask)
            .where(DigestTask.status.in_([TaskStatus.QUEUED.value, TaskStatus.RUNNING.value]))
        )
        or 0
    )


def _validate_scope(db, feed_codes: list[str] | None) -> list[str] | None:
    if not feed_codes:
        return None
    known = set(db.scalars(select(Feed.code)))
    unknown = [code for code in feed_codes if code not in known]
    if unknown:
        raise AppError("VALIDATION", 422, detail={"unknown_feeds": unknown})
    inactive = [
        feed.code
        for feed in db.scalars(select(Feed).where(Feed.code.in_(feed_codes)))
        if not feed.active
    ]
    if inactive:
        raise AppError("FEED_INACTIVE", 422, detail={"inactive_feeds": inactive})
    return feed_codes


def create_task(db, mode: str, feed_codes: list[str] | None, principal: dict, ip: str | None = None) -> DigestTask:
    if mode not in {item.value for item in TaskMode}:
        raise AppError("VALIDATION", 422, detail=f"mode={mode}")
    if running_count(db) > 0:
        raise AppError("TASK_BUSY", 409, detail="已有批次在运行，请等待完成")

    scope = _validate_scope(db, feed_codes)
    task = DigestTask(
        code=digest_service.next_task_code(db),
        mode=mode,
        status=TaskStatus.QUEUED.value,
        feed_scope=",".join(scope) if scope else "all",
        triggered_by=principal["email"],
        triggered_role=principal["role"],
        log_lines=[],
    )
    db.add(task)
    db.flush()
    db.commit()

    dispatched = dispatch(task.id)
    db.refresh(task)
    if not dispatched:
        logger.info("celery 不可用，批次 %s 内联执行", task.code)
        with SessionLocal() as inline_db:
            inline_task = inline_db.get(DigestTask, task.id)
            if inline_task is not None:
                digest_service.execute_task(inline_db, inline_task)
        db.refresh(task)
    return task


def dispatch(task_id: int) -> bool:
    try:
        celery_app.send_task(TASK_RUN_DIGEST, args=[task_id])
        return True
    except Exception as exc:  # noqa: BLE001 - broker 掉了也要能跑
        logger.warning("send_task 失败，降级内联执行: %s", exc)
        return False

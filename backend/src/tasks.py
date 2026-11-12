"""Celery 任务：心跳 + 采集/解析批次。"""
from __future__ import annotations

import time

from src.config.celery_app import TASK_HEARTBEAT, TASK_RUN_DIGEST, celery_app
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("tasks")


def _redis():
    import redis

    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@celery_app.task(name=TASK_HEARTBEAT)
def heartbeat() -> str:
    try:
        _redis().set("podcastdig:worker:heartbeat", time.time())
        return "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("heartbeat failed: %s", exc)
        return "error"


@celery_app.task(name=TASK_RUN_DIGEST)
def run_digest(task_id: int) -> dict:
    """worker 侧执行采集/解析批次；批次状态与日志都落 MySQL，前端轮询。"""
    from src.config.database import SessionLocal
    from src.models.digest_task import DigestTask
    from src.services import digest_service

    with SessionLocal() as db:
        task = db.get(DigestTask, task_id)
        if task is None:
            logger.warning("task %s not found", task_id)
            return {"status": "missing", "task_id": task_id}
        finished = digest_service.execute_task(db, task)
        return {
            "status": finished.status,
            "task_id": task_id,
            "episodes_scanned": finished.episodes_scanned,
            "chapters_parsed": finished.chapters_parsed,
            "issues_found": finished.issues_found,
        }

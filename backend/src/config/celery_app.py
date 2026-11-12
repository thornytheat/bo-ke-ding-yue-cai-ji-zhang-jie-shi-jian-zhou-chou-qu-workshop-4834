"""Celery 入口：backend 投递采集/解析批次，worker 容器消费（beat 写心跳）。"""
from __future__ import annotations

from celery import Celery

from src.config.settings import settings

celery_app = Celery(
    "podcastdig",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
    task_soft_time_limit=180,
    task_time_limit=240,
)

celery_app.conf.beat_schedule = {
    "podcastdig-heartbeat": {"task": "podcastdig.heartbeat", "schedule": 20.0},
}

TASK_HEARTBEAT = "podcastdig.heartbeat"
TASK_RUN_DIGEST = "podcastdig.run_digest"
TASK_RESCAN_ISSUES = "podcastdig.rescan_issues"

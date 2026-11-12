"""采集/解析批次 controller。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, task_service


def list_tasks(db: Session, limit: int = 30) -> dict:
    return {"items": task_service.list_tasks(db, limit)}


def get_task(db: Session, code: str) -> dict:
    return {"task": task_service.task_to_dict(task_service.get_task(db, code))}


def run_task(db: Session, payload: dict, principal: dict, request: Request) -> dict:
    task = task_service.create_task(
        db,
        payload.get("mode", "both"),
        payload.get("feed_codes"),
        principal,
        ip=request.client.host if request.client else None,
    )
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="task.run",
        entity="digest_task",
        entity_id=task.code,
        detail={
            "mode": task.mode,
            "status": task.status,
            "episodes_new": task.episodes_new,
            "episodes_updated": task.episodes_updated,
        },
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return {"task": task_service.task_to_dict(task)}

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import READ_ROLES, TASK_RUN_ROLES
from src.controllers import task_controller
from src.middlewares.rbac import require_roles
from src.schemas.task import TaskRunIn

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
def list_tasks(
    limit: int = Query(default=30, ge=1, le=200),
    principal: dict = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return task_controller.list_tasks(db, limit)


@router.get("/{code}")
def get_task(
    code: str,
    principal: dict = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return task_controller.get_task(db, code)


@router.post("/run")
def run_task(
    payload: TaskRunIn,
    request: Request,
    principal: dict = Depends(require_roles(*TASK_RUN_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return task_controller.run_task(db, payload.model_dump(), principal, request)

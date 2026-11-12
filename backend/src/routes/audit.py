from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import AUDIT_ROLES
from src.controllers import audit_controller
from src.middlewares.rbac import require_roles

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_logs(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=40, ge=1, le=200),
    action: str | None = None,
    principal: dict = Depends(require_roles(*AUDIT_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return audit_controller.list_logs(db, page, size, action)

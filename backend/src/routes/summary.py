from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import READ_ROLES
from src.controllers import dashboard_controller
from src.middlewares.rbac import require_roles

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("")
def overview(
    principal: dict = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return dashboard_controller.overview(db)

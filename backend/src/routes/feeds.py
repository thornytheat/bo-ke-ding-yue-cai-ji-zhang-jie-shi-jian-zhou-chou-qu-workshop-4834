from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import FEED_WRITE_ROLES, READ_ROLES
from src.controllers import feed_controller
from src.middlewares.rbac import require_roles
from src.schemas.feed import FeedPatchIn

router = APIRouter(prefix="/feeds", tags=["feeds"])


@router.get("")
def list_feeds(
    principal: dict = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return feed_controller.list_feeds(db)


@router.get("/{code}")
def get_feed(
    code: str,
    principal: dict = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return feed_controller.get_feed(db, code)


@router.get("/{code}/preview")
def preview_feed(
    code: str,
    principal: dict = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return feed_controller.preview_feed(db, code)


@router.patch("/{code}")
def patch_feed(
    code: str,
    payload: FeedPatchIn,
    request: Request,
    principal: dict = Depends(require_roles(*FEED_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return feed_controller.patch_feed(db, code, payload.model_dump(exclude_none=True), principal, request)

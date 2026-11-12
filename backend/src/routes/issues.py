from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import ISSUE_RESOLVE_ROLES, READ_ROLES
from src.controllers import issue_controller
from src.middlewares.rbac import require_roles
from src.schemas.issue import IssueResolveIn

router = APIRouter(prefix="/issues", tags=["issues"])


@router.get("")
def list_issues(
    kind: str | None = None,
    status: str | None = None,
    episode: str | None = None,
    feed: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    principal: dict = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return issue_controller.list_issues(db, kind, status, episode, feed, page, size)


@router.get("/summary")
def summary(
    principal: dict = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return issue_controller.summary(db)


@router.post("/rescan")
def rescan(
    request: Request,
    principal: dict = Depends(require_roles(*ISSUE_RESOLVE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return issue_controller.rescan(db, principal, request)


@router.post("/{issue_id}/resolve")
def resolve(
    issue_id: int,
    payload: IssueResolveIn,
    request: Request,
    principal: dict = Depends(require_roles(*ISSUE_RESOLVE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return issue_controller.resolve_issue(db, issue_id, payload.note, principal, request)

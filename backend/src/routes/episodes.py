from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.limits import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.constants.roles import CHAPTER_WRITE_ROLES, EPISODE_WRITE_ROLES, READ_ROLES
from src.controllers import chapter_controller, episode_controller
from src.middlewares.rbac import require_roles
from src.schemas.episode import ChapterCreateIn, ChapterPatchIn

router = APIRouter(prefix="/episodes", tags=["episodes"])


@router.get("")
def list_episodes(
    feed: str | None = None,
    status: str | None = None,
    ingest_state: str | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    principal: dict = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return episode_controller.list_episodes(db, feed, status, ingest_state, q, page, size)


@router.get("/{code}")
def get_episode(
    code: str,
    principal: dict = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return episode_controller.get_episode(db, code)


@router.post("/{code}/reparse")
def reparse_episode(
    code: str,
    request: Request,
    principal: dict = Depends(require_roles(*EPISODE_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return episode_controller.reparse_episode(db, code, principal, request)


@router.post("/{code}/normalize")
def normalize_episode(
    code: str,
    request: Request,
    principal: dict = Depends(require_roles(*EPISODE_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return episode_controller.normalize_episode(db, code, principal, request)


@router.post("/{code}/chapters")
def create_chapter(
    code: str,
    payload: ChapterCreateIn,
    request: Request,
    principal: dict = Depends(require_roles(*CHAPTER_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return chapter_controller.create_chapter(db, code, payload.model_dump(exclude_none=True), principal, request)


@router.patch("/{code}/chapters/{chapter_id}")
def update_chapter(
    code: str,
    chapter_id: int,
    payload: ChapterPatchIn,
    request: Request,
    principal: dict = Depends(require_roles(*CHAPTER_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return chapter_controller.update_chapter(
        db, code, chapter_id, payload.model_dump(exclude_none=True), principal, request
    )


@router.delete("/{code}/chapters/{chapter_id}")
def delete_chapter(
    code: str,
    chapter_id: int,
    request: Request,
    principal: dict = Depends(require_roles(*CHAPTER_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    return chapter_controller.delete_chapter(db, code, chapter_id, principal, request)

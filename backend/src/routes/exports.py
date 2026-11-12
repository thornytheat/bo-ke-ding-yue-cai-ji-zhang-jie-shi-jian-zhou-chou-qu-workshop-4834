from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import EXPORT_ROLES
from src.controllers import export_controller
from src.middlewares.rbac import require_roles

router = APIRouter(prefix="/exports", tags=["exports"])


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/clip-list.csv")
def clip_list(
    request: Request,
    principal: dict = Depends(require_roles(*EXPORT_ROLES)),
    db: Session = Depends(get_db),
) -> Response:
    content, filename = export_controller.clip_list(db, principal, request)
    return _csv_response(content, filename)


@router.get("/chapter-cuts.csv")
def chapter_cuts(
    request: Request,
    principal: dict = Depends(require_roles(*EXPORT_ROLES)),
    db: Session = Depends(get_db),
) -> Response:
    content, filename = export_controller.chapter_cuts(db, principal, request)
    return _csv_response(content, filename)


@router.get("/issues.csv")
def issues(
    request: Request,
    principal: dict = Depends(require_roles(*EXPORT_ROLES)),
    db: Session = Depends(get_db),
) -> Response:
    content, filename = export_controller.issues(db, principal, request)
    return _csv_response(content, filename)

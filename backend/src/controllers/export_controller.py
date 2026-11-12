"""导出 controller：三种 CSV，每次导出都写审计 + 共享卷留档。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, export_service


def _serve(db, principal: dict, request: Request, kind: str, filename: str) -> tuple[str, str]:
    if kind == "clip-list":
        content, rows = export_service.clip_list_csv(db)
    elif kind == "chapter-cuts":
        content, rows = export_service.chapter_cuts_csv(db)
    else:
        content, rows = export_service.issues_csv(db)
    export_service.write_artifact(f"{kind}.csv", content)
    if rows == 0:
        from src.utils.errors import AppError

        raise AppError("EXPORT_EMPTY", 422, detail=kind)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action=f"export.{kind}",
        entity="export",
        entity_id=kind,
        detail={"rows": rows, "filename": filename},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return content, filename


def clip_list(db: Session, principal: dict, request: Request) -> tuple[str, str]:
    return _serve(db, principal, request, "clip-list", "podcastdig-clip-list.csv")


def chapter_cuts(db: Session, principal: dict, request: Request) -> tuple[str, str]:
    return _serve(db, principal, request, "chapter-cuts", "podcastdig-chapter-cuts.csv")


def issues(db: Session, principal: dict, request: Request) -> tuple[str, str]:
    return _serve(db, principal, request, "issues", "podcastdig-issues.csv")

"""异常工单 controller：列表 / 汇总 / 处置 / 全量复扫。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, issue_service


def list_issues(
    db: Session,
    kind: str | None,
    status: str | None,
    episode_code: str | None,
    feed_code: str | None,
    page: int,
    size: int,
) -> dict:
    return issue_service.list_issues(db, kind, status, episode_code, feed_code, page, size)


def summary(db: Session) -> dict:
    return issue_service.issue_summary(db)


def resolve_issue(db: Session, issue_id: int, note: str, principal: dict, request: Request) -> dict:
    result = issue_service.resolve_issue(db, issue_id, note, principal["email"])
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="issue.resolve",
        entity="chapter_issue",
        entity_id=str(issue_id),
        detail={"note": note},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return {"issue": result, "summary": issue_service.issue_summary(db)}


def rescan(db: Session, principal: dict, request: Request) -> dict:
    result = issue_service.rescan_all(db)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="issue.rescan",
        entity="chapter_issue",
        entity_id="all",
        detail={"open": result["open"], "resolved": result["resolved"]},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return result

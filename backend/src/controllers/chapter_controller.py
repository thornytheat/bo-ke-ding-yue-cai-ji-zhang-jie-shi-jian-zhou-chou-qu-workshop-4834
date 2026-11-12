"""章节 controller：内联新增 / 修改 / 删除。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, chapter_service, episode_service


def _audit(db, principal, action, code, chapter_id, detail, request) -> None:
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action=action,
        entity="chapter",
        entity_id=f"{code}:{chapter_id}",
        detail=detail,
        ip=request.client.host if request.client else None,
    )


def create_chapter(db: Session, code: str, payload: dict, principal: dict, request: Request) -> dict:
    result = chapter_service.add_chapter(db, code, payload, principal["email"])
    _audit(db, principal, "chapter.create", code, result["chapter_id"], payload, request)
    db.commit()
    return {"result": result, "episode": episode_service.episode_detail(db, code)}


def update_chapter(
    db: Session, code: str, chapter_id: int, payload: dict, principal: dict, request: Request
) -> dict:
    result = chapter_service.update_chapter(db, code, chapter_id, payload, principal["email"])
    _audit(db, principal, "chapter.update", code, chapter_id, payload, request)
    db.commit()
    return {"result": result, "episode": episode_service.episode_detail(db, code)}


def delete_chapter(db: Session, code: str, chapter_id: int, principal: dict, request: Request) -> dict:
    result = chapter_service.delete_chapter(db, code, chapter_id, principal["email"])
    _audit(db, principal, "chapter.delete", code, chapter_id, {}, request)
    db.commit()
    return {"result": result, "episode": episode_service.episode_detail(db, code)}

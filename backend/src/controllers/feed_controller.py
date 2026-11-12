"""订阅源 controller：列表 / 详情 / 配置 / 抓取预览。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, feed_service


def list_feeds(db: Session) -> dict:
    return {"items": feed_service.list_feeds(db)}


def get_feed(db: Session, code: str) -> dict:
    feed = feed_service.get_feed(db, code)
    return {"feed": feed_service.feed_to_dict(db, feed)}


def patch_feed(db: Session, code: str, payload: dict, principal: dict, request: Request) -> dict:
    feed = feed_service.update_feed(db, code, payload)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="feed.update",
        entity="feed",
        entity_id=code,
        detail={key: value for key, value in payload.items() if value is not None},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return {"feed": feed}


def preview_feed(db: Session, code: str) -> dict:
    return feed_service.preview_feed(db, code)

"""认证 controller：登录 / 当前用户。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, auth_service


def login(db: Session, email: str, password: str, request: Request) -> dict:
    user = auth_service.authenticate(db, email, password)
    payload = auth_service.issue_token(user)
    audit_service.record(
        db,
        actor_email=user.email,
        actor_role=user.role,
        action="auth.login",
        entity="user",
        entity_id=str(user.id),
        detail={"role": user.role},
        layer="auth",
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return payload


def me(db: Session, email: str) -> dict:
    user = auth_service.find_user(db, email)
    return {"user": auth_service.user_payload(user)}

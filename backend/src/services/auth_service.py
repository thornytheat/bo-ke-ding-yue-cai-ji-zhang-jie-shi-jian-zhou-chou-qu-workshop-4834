"""认证服务：登录、当前用户。"""
from __future__ import annotations

from sqlalchemy import select

from src.constants.enums import ROLE_LABELS
from src.constants.roles import permissions_of
from src.models.user import User
from src.utils.errors import AppError
from src.utils.security import create_access_token, verify_password


def authenticate(db, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise AppError("AUTH_INVALID", 401)
    return user


def issue_token(user: User) -> dict:
    token, expires_in = create_access_token(user.email, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": user_payload(user),
    }


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, user.role),
        "permissions": permissions_of(user.role),
    }


def find_user(db, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise AppError("AUTH_MISSING", 401)
    return user

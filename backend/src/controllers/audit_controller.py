"""审计 controller：只读查询（仅运营主管）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import audit_service


def list_logs(db: Session, page: int, size: int, action: str | None) -> dict:
    return audit_service.list_logs(db, page, size, action)

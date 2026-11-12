"""看板 controller：顶部口径聚合。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import summary_service


def overview(db: Session) -> dict:
    return summary_service.overview(db)

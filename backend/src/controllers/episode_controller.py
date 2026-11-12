"""单集 controller：列表 / 详情 / 重解析 / 不变量修正。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, episode_service


def list_episodes(
    db: Session,
    feed_code: str | None,
    parse_status: str | None,
    ingest_state: str | None,
    query: str | None,
    page: int,
    size: int,
) -> dict:
    return episode_service.list_episodes(db, feed_code, parse_status, ingest_state, query, page, size)


def get_episode(db: Session, code: str) -> dict:
    return episode_service.episode_detail(db, code)


def reparse_episode(db: Session, code: str, principal: dict, request: Request) -> dict:
    result = episode_service.reparse_episode(db, code)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="episode.reparse",
        entity="episode",
        entity_id=code,
        detail={
            "entries": result["entries"],
            "unparsed": result["unparsed"],
            "about_minutes": result["about_minutes"],
        },
        ip=request.client.host if request.client else None,
    )
    db.commit()
    result["episode"] = episode_service.episode_detail(db, code)["episode"]
    return result


def normalize_episode(db: Session, code: str, principal: dict, request: Request) -> dict:
    result = episode_service.normalize_episode(db, code)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="chapter.normalize",
        entity="episode",
        entity_id=code,
        detail={
            "reordered": result["reordered"],
            "merged": result["merged"],
            "folded": result["folded"],
            "open_issues": result["open_issues"],
        },
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return result

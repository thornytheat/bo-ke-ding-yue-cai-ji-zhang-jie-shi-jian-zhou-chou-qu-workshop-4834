"""审计服务：领域动作逐条落库（HTTP 层另有 AuditMiddleware 兜底）。"""
from __future__ import annotations

from sqlalchemy import func, select

from src.models.audit import AuditLog


def record(
    db,
    actor_email: str,
    actor_role: str,
    action: str,
    entity: str,
    entity_id: str | None = None,
    detail: dict | None = None,
    layer: str = "domain",
    ip: str | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_email=actor_email,
        actor_role=actor_role,
        action=action,
        entity=entity,
        entity_id=entity_id,
        detail=detail or {},
        layer=layer,
        ip=ip,
    )
    db.add(log)
    db.flush()
    return log


def list_logs(db, page: int = 1, size: int = 40, action: str | None = None) -> dict:
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(stmt.order_by(AuditLog.id.desc()).offset((page - 1) * size).limit(size))
    )
    return {
        "items": [
            {
                "id": row.id,
                "actor_email": row.actor_email,
                "actor_role": row.actor_role,
                "action": row.action,
                "entity": row.entity,
                "entity_id": row.entity_id,
                "detail": row.detail,
                "layer": row.layer,
                "ip": row.ip,
                "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else None,
            }
            for row in rows
        ],
        "total": total,
        "page": page,
        "size": size,
    }

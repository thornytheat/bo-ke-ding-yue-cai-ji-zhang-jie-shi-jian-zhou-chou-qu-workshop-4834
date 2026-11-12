"""角色 -> 权限点映射。README 与前端 constants/roles.ts 同步。"""
from __future__ import annotations

from src.constants.enums import ROLE_LABELS, Role

PERMISSIONS: dict[str, set[str]] = {
    Role.ADMIN.value: {
        "feed:write", "task:run", "episode:write", "chapter:write",
        "issue:resolve", "export:read", "audit:read", "library:read",
    },
    Role.ANALYST.value: {
        "task:run", "episode:write", "chapter:write", "issue:resolve",
        "export:read", "library:read",
    },
    Role.VIEWER.value: {"library:read", "export:read"},
}

# route / controller 层使用的角色白名单
READ_ROLES = (Role.ADMIN.value, Role.ANALYST.value, Role.VIEWER.value)
FEED_WRITE_ROLES = (Role.ADMIN.value,)
TASK_RUN_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
CHAPTER_WRITE_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
EPISODE_WRITE_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
ISSUE_RESOLVE_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
EXPORT_ROLES = (Role.ADMIN.value, Role.ANALYST.value, Role.VIEWER.value)
AUDIT_ROLES = (Role.ADMIN.value,)


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


def role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


def permissions_of(role: str) -> list[str]:
    return sorted(PERMISSIONS.get(role, set()))

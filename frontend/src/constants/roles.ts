/** 角色 -> 权限点。后端唯一定义处：backend/src/constants/roles.py */
import type { Role } from '../types/models';

export const PERMISSIONS: Record<Role, string[]> = {
  admin: [
    'feed:write',
    'task:run',
    'episode:write',
    'chapter:write',
    'issue:resolve',
    'export:read',
    'audit:read',
    'library:read',
  ],
  analyst: ['task:run', 'episode:write', 'chapter:write', 'issue:resolve', 'export:read', 'library:read'],
  viewer: ['library:read', 'export:read'],
};

export function can(role: Role | undefined, permission: string): boolean {
  if (!role) return false;
  return PERMISSIONS[role].includes(permission);
}

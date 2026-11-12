import { useSyncExternalStore } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { authStore } from '../stores/authStore';
import { ROLE_LABELS } from '../constants/enums';
import { can } from '../constants/roles';

export function useAuth() {
  return useSyncExternalStore(authStore.subscribe, authStore.getState);
}

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const state = useAuth();
  const location = useLocation();
  if (!state.bootstrapped) {
    return <div className="boot">正在装载磁带 …</div>;
  }
  if (!state.token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

export function RequirePermission({
  permission,
  children,
}: {
  permission: string;
  children: React.ReactNode;
}) {
  const state = useAuth();
  if (!state.user || !can(state.user.role, permission)) {
    return (
      <div className="forbidden" data-testid="forbidden">
        <div>
          <div className="eyebrow">403 · FORBIDDEN</div>
          <h1>这盘磁带不在你的权限范围</h1>
          <p className="muted">
            当前角色「{state.user ? ROLE_LABELS[state.user.role] : '访客'}」没有 {permission} 权限。
            剪辑师可以只读节目库、章节时间轴与剪辑清单导出；采集运行、章节修改与异常处置属于内容运营 / 运营主管。
          </p>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}

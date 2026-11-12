import { NavLink, useNavigate } from 'react-router-dom';
import ReelMark from '../common/ReelMark';
import Toasts from '../common/Toasts';
import { NAV_ITEMS, STUDIO } from '../../constants/ui';
import { ROLE_LABELS } from '../../constants/enums';
import { can } from '../../constants/roles';
import { authStore } from '../../stores/authStore';
import { useAuth } from '../../router/guards';

/** 壳体：左侧 REEL 导轨 + 主内容区。窄屏时导轨折叠成顶部横条。 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const state = useAuth();
  const navigate = useNavigate();
  const role = state.user?.role;

  const logout = () => {
    authStore.logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="shell">
      <aside className="rail">
        <div className="rail-top">
          <div className="rail-mark">
            <ReelMark size={44} />
            <span>PD</span>
            <small>REEL 07 · A</small>
          </div>
          <div className="rail-studio">
            <b>{STUDIO}</b>
            <span>节目运营组 · 6 人</span>
          </div>
        </div>

        <nav className="rail-nav" aria-label="主导航">
          {NAV_ITEMS.filter((item) => can(role, item.permission)).map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
              <span className="rail-reel">{item.reel}</span>
              <span className="rail-label">{item.label}</span>
              <span className="rail-sub">{item.sub}</span>
            </NavLink>
          ))}
        </nav>

        <div className="rail-foot">
          <div className="rail-who">
            <span className="mono">{state.user?.display_name ?? '—'}</span>
            <span>{state.user ? ROLE_LABELS[state.user.role] : ''}</span>
          </div>
          <button type="button" className="btn btn-quiet" onClick={logout}>
            退出
          </button>
          <p className="rail-note">章节时间轴 · 演示环境</p>
        </div>
      </aside>

      <main className="main">{children}</main>
      <Toasts />
    </div>
  );
}

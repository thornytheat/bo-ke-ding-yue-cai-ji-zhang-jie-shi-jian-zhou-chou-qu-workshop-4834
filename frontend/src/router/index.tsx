import { Navigate, Route, Routes } from 'react-router-dom';
import AppShell from '../components/layout/AppShell';
import EpisodeDetail from '../pages/EpisodeDetail';
import Feeds from '../pages/Feeds';
import Issues from '../pages/Issues';
import Library from '../pages/Library';
import Login from '../pages/Login';
import { RequireAuth, RequirePermission } from './guards';

function Protected({ permission, children }: { permission: string; children: React.ReactNode }) {
  return (
    <RequireAuth>
      <AppShell>
        <RequirePermission permission={permission}>{children}</RequirePermission>
      </AppShell>
    </RequireAuth>
  );
}

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Navigate to="/library" replace />} />
      <Route
        path="/library"
        element={
          <Protected permission="library:read">
            <Library />
          </Protected>
        }
      />
      <Route
        path="/episodes/:code"
        element={
          <Protected permission="library:read">
            <EpisodeDetail />
          </Protected>
        }
      />
      <Route
        path="/feeds"
        element={
          <Protected permission="library:read">
            <Feeds />
          </Protected>
        }
      />
      <Route
        path="/issues"
        element={
          <Protected permission="library:read">
            <Issues />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/library" replace />} />
    </Routes>
  );
}

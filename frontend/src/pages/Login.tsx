import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ReelMark from '../components/common/ReelMark';
import { authApi } from '../api/auth';
import { authStore } from '../stores/authStore';
import { errorMessage } from '../utils/errorMessage';
import { DEMO_ACCOUNTS, DEMO_PASSWORD, STUDIO } from '../constants/ui';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('admin@podcastdig.io');
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await authApi.login(email.trim(), password);
      authStore.setSession(result.access_token, result.user);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from !== '/login' ? from : '/library', { replace: true });
    } catch (err) {
      setError(errorMessage((err as { payload?: unknown })?.payload, '登录失败，请检查邮箱与密码'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <section className="login-sleeve">
        <div className="sleeve-head">
          <div>
            <div className="eyebrow">TAPE 07 · SIDE A · 2026</div>
            <h1 className="sleeve-title">
              把 show notes
              <br />
              变成能切的时间轴
            </h1>
          </div>
          <ReelMark size={104} spinning />
        </div>

        <p className="sleeve-lede">
          {STUDIO} · 节目运营组 6 人，运营 9 档中文播客。每周把 RSS / 平台接口 / 目录页里的新单集收进来，
          把 show notes 里的「01:23:45」「1h02m」「约 12 分钟处」拆成剪辑师能直接用的章节时间点。
        </p>

        <div className="sleeve-ticks" aria-hidden>
          {Array.from({ length: 28 }).map((_, index) => (
            <i key={index} className={index % 4 === 0 ? 'major' : ''} />
          ))}
        </div>

        <ul className="sleeve-accounts">
          {DEMO_ACCOUNTS.map((account) => (
            <li key={account.email}>
              <button
                type="button"
                className={email === account.email ? 'account-chip is-active' : 'account-chip'}
                onClick={() => {
                  setEmail(account.email);
                  setPassword(DEMO_PASSWORD);
                }}
              >
                <span className="account-role">{account.role}</span>
                <span className="account-mail mono">{account.email}</span>
                <span className="account-note">{account.note}</span>
              </button>
            </li>
          ))}
        </ul>
        <p className="sleeve-foot mono">统一口令 {DEMO_PASSWORD} · 演示数据每次启动幂等重建</p>
      </section>

      <section className="login-panel">
        <form className="login-form" onSubmit={submit}>
          <div className="eyebrow">STUDIO LOGIN</div>
          <h2>登录工坊</h2>
          <label className="field">
            <span>工作邮箱</span>
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>口令</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <button className="btn btn-primary btn-wide" type="submit" disabled={busy}>
            {busy ? '走带中 …' : '进入工坊'}
          </button>

          <p className="login-hint">
            剪辑师账号进入后是只读视图：能看章节时间轴、异常队列与导出剪辑清单，不能运行采集或修改章节。
          </p>
        </form>
      </section>
    </div>
  );
}

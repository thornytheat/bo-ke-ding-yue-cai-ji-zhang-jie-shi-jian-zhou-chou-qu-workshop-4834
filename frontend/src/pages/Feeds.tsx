import { useState } from 'react';
import PageHead from '../components/common/PageHead';
import ReelMark from '../components/common/ReelMark';
import StatusPill from '../components/common/StatusPill';
import TapeLabel from '../components/common/TapeLabel';
import EmptyState from '../components/common/EmptyState';
import { feedApi, summaryApi } from '../api/feeds';
import { taskApi } from '../api/tasks';
import { useAsync } from '../hooks/useAsync';
import { usePolling } from '../hooks/usePolling';
import { useAuth } from '../router/guards';
import { can } from '../constants/roles';
import { FEEDS_HINT } from '../constants/ui';
import { TASK_STATUS_LABELS } from '../constants/enums';
import { errorMessage } from '../utils/errorMessage';
import { relativeTime } from '../utils/format';
import { uiStore } from '../stores/uiStore';
import type { FeedPreview, TaskItem } from '../types/models';

function taskTone(status: string) {
  if (status === 'success') return 'ok' as const;
  if (status === 'failed') return 'bad' as const;
  if (status === 'running') return 'tape' as const;
  return 'muted' as const;
}

export default function Feeds() {
  const state = useAuth();
  const canRun = can(state.user?.role, 'task:run');
  const canWriteFeed = can(state.user?.role, 'feed:write');

  const [mode, setMode] = useState<'ingest' | 'parse' | 'both'>('ingest');
  const [scope, setScope] = useState('');
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<FeedPreview | null>(null);

  const feeds = useAsync(() => feedApi.list(), []);
  const tasks = useAsync(() => taskApi.list(8), []);
  const overview = useAsync(() => summaryApi.overview(), []);

  const running = (tasks.data?.items ?? []).some(
    (task) => task.status === 'queued' || task.status === 'running',
  );
  const latest = tasks.data?.items?.[0] ?? null;

  usePolling(
    () => {
      tasks.reload();
      feeds.reload();
      overview.reload();
    },
    1600,
    running,
  );

  const runTask = async () => {
    setBusy(true);
    try {
      const result = await taskApi.run(mode, scope ? [scope] : undefined);
      uiStore.toast(`${result.task.code} 已投递（${result.task.mode_label}）`);
      tasks.reload();
      feeds.reload();
      overview.reload();
    } catch (error) {
      uiStore.toast(errorMessage((error as { payload?: unknown })?.payload, '批次投递失败'), 'bad');
    } finally {
      setBusy(false);
    }
  };

  const openPreview = async (code: string) => {
    try {
      const result = await feedApi.preview(code);
      setPreview(result);
    } catch (error) {
      uiStore.toast(errorMessage((error as { payload?: unknown })?.payload, '预览失败'), 'bad');
    }
  };

  const toggleFeed = async (code: string, active: boolean) => {
    try {
      await feedApi.patch(code, { active });
      uiStore.toast(active ? '订阅源已启用' : '订阅源已停用');
      feeds.reload();
    } catch (error) {
      uiStore.toast(errorMessage((error as { payload?: unknown })?.payload, '更新失败'), 'bad');
    }
  };

  return (
    <>
      <PageHead
        eyebrow="SUBSCRIPTIONS · 订阅源"
        title="订阅源与采集任务"
        lede={FEEDS_HINT}
        meta={
          <>
            <span className="chip mono">{overview.data?.feeds ?? '—'} 个源</span>
            <span className="chip mono">{overview.data?.pending_ingest ?? '—'} 待入库</span>
            <span className="chip mono">{overview.data?.episodes ?? '—'} 集</span>
            {running && <StatusPill tone="tape" dot>批次运行中</StatusPill>}
          </>
        }
      />

      <section className="run-panel">
        <div className="run-controls">
          <TapeLabel
            eyebrow="DIGEST RUN · 跑一次"
            title="采集 / 解析"
            meta={<span className="mono">投递到 Celery worker，前端轮询批次状态</span>}
            tone="plain"
          />
          <div className="run-form">
            <label className="field field-inline">
              <span>批次模式</span>
              <select value={mode} onChange={(event) => setMode(event.target.value as never)}>
                <option value="ingest">采集（读夹具 / 比对指纹）</option>
                <option value="parse">解析（时间戳 + 不变量校验）</option>
                <option value="both">采集 + 解析</option>
              </select>
            </label>
            <label className="field field-inline">
              <span>订阅源范围</span>
              <select value={scope} onChange={(event) => setScope(event.target.value)}>
                <option value="">全部启用源</option>
                {(feeds.data?.items ?? []).map((feed) => (
                  <option key={feed.code} value={feed.code}>
                    {feed.show_name}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className="btn btn-primary" disabled={!canRun || busy || running} onClick={runTask}>
              {busy || running ? '走带中 …' : '运行批次'}
            </button>
            {!canRun && <span className="muted small">剪辑师只读，运行批次需要内容运营 / 运营主管。</span>}
          </div>
        </div>

        <div className={`run-meter ${running ? 'is-running' : ''}`}>
          <ReelMark size={78} spinning={running} />
          {latest ? (
            <>
              <div className="run-code mono">{latest.code}</div>
              <StatusPill tone={taskTone(latest.status)}>{TASK_STATUS_LABELS[latest.status] ?? latest.status}</StatusPill>
              <dl className="run-stats">
                <div>
                  <dt>扫描</dt>
                  <dd className="mono">{latest.episodes_scanned}</dd>
                </div>
                <div>
                  <dt>新增</dt>
                  <dd className="mono">{latest.episodes_new}</dd>
                </div>
                <div>
                  <dt>更新</dt>
                  <dd className="mono">{latest.episodes_updated}</dd>
                </div>
                <div>
                  <dt>章节</dt>
                  <dd className="mono">{latest.chapters_parsed}</dd>
                </div>
                <div>
                  <dt>未识别</dt>
                  <dd className="mono">{latest.unparsed_chapters}</dd>
                </div>
                <div>
                  <dt>异常</dt>
                  <dd className="mono">{latest.issues_found}</dd>
                </div>
              </dl>
              <p className="run-note mono">{relativeTime(latest.finished_at ?? latest.created_at)} · 耗时 {latest.duration_ms} ms</p>
            </>
          ) : (
            <p className="muted">还没有批次记录，点「运行批次」开始。</p>
          )}
        </div>
      </section>

      <TapeLabel
        eyebrow="FEEDS · 源清单"
        title="三类订阅源"
        meta={<span className="mono">RSS XML × 3 · 平台 JSON × 2 · 目录 HTML × 1</span>}
      />

      {feeds.error ? (
        <EmptyState
          tone="error"
          title="订阅源列表读不出来"
          hint={errorMessage((feeds.error as { payload?: unknown })?.payload, '接口返回异常')}
          actionLabel="重试"
          onAction={feeds.reload}
        />
      ) : (
        <div className="feed-grid">
          {(feeds.data?.items ?? []).map((feed, index) => (
            <article key={feed.code} className={`feed-row ${feed.active ? '' : 'is-off'}`}>
              <header className="feed-head">
                <span className="reel-tag mono">REEL {String(index + 1).padStart(2, '0')}</span>
                <h3>{feed.show_name}</h3>
                <StatusPill tone="muted">{feed.kind_label}</StatusPill>
                {feed.active ? <StatusPill tone="ok" dot>启用</StatusPill> : <StatusPill tone="muted">停用</StatusPill>}
              </header>
              <p className="feed-url mono">{feed.url}</p>
              <div className="feed-stats">
                <span className="mono">{feed.episode_count} 集</span>
                <span className="mono">{feed.chapter_count} 章</span>
                <span className="mono">{feed.open_issues} 异常</span>
                {feed.pending_episodes > 0 && (
                  <StatusPill tone="info">{feed.pending_episodes} 待入库</StatusPill>
                )}
                {feed.last_status === 'error' && <StatusPill tone="bad" dot>最近抓取失败</StatusPill>}
              </div>
              <p className="feed-note">
                {feed.note}
                <br />
                <span className="mono muted">
                  {feed.cadence} · 主播 {feed.host} · 最近抓取 {relativeTime(feed.last_fetch_at)}
                </span>
              </p>
              <div className="feed-actions">
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => openPreview(feed.code)}>
                  抓取预览
                </button>
                {canWriteFeed && (
                  <button
                    type="button"
                    className="btn btn-quiet btn-sm"
                    onClick={() => toggleFeed(feed.code, !feed.active)}
                  >
                    {feed.active ? '停用' : '启用'}
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {preview && (
        <section className="preview-panel">
          <TapeLabel
            eyebrow="DRY RUN · 抓取预览"
            title={`${preview.feed.show_name} · 扫描 ${preview.scanned} 条`}
            meta={<span className="mono">不落库：只读夹具并按内容指纹比对</span>}
            actions={
              <button type="button" className="btn btn-quiet" onClick={() => setPreview(null)}>
                关闭
              </button>
            }
          />
          <div className="preview-cols">
            <div>
              <h4>新增 {preview.created.length}</h4>
              <ul className="preview-list">
                {preview.created.length === 0 && <li className="muted">没有新单集</li>}
                {preview.created.map((item) => (
                  <li key={item.guid}>
                    <span className="mono">{item.episode_code ?? 'NEW'}</span> {item.title}
                    {item.reason && <em className="muted"> · {item.reason}</em>}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4>更新 {preview.updated.length}</h4>
              <ul className="preview-list">
                {preview.updated.length === 0 && <li className="muted">没有内容变更</li>}
                {preview.updated.map((item) => (
                  <li key={item.guid}>
                    <span className="mono">{item.episode_code}</span> {item.title}
                    <ul className="diff-list">
                      {item.changes.map((change) => (
                        <li key={change.field}>
                          <b className="mono">{change.field}</b>：{String(change.from ?? '')} → {String(change.to ?? '')}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4>不变 {preview.unchanged}</h4>
              <p className="muted">内容指纹一致，采集时不会写入。</p>
            </div>
          </div>
        </section>
      )}

      <TapeLabel
        eyebrow="RUN LOG · 批次账本"
        title="最近批次"
        meta={<span className="mono">{tasks.data?.items.length ?? 0} 条记录</span>}
      />

      <div className="task-list">
        {(tasks.data?.items ?? []).map((task: TaskItem) => (
          <details key={task.id} className="task-row" open={task.status === 'running'}>
            <summary>
              <span className="mono task-code">{task.code}</span>
              <span className="task-mode">{task.mode_label}</span>
              <StatusPill tone={taskTone(task.status)}>{TASK_STATUS_LABELS[task.status] ?? task.status}</StatusPill>
              <span className="mono task-nums">
                扫描 {task.episodes_scanned} / 新增 {task.episodes_new} / 更新 {task.episodes_updated} / 章节{' '}
                {task.chapters_parsed} / 异常 {task.issues_found}
              </span>
              <span className="mono muted task-when">{relativeTime(task.finished_at ?? task.created_at)}</span>
            </summary>
            {task.error_text && <p className="task-error">{task.error_text}</p>}
            <ul className="task-log">
              {(task.log_lines ?? []).map((line, index) => (
                <li key={index} className={`log-${line.level}`}>
                  <span className="mono">{line.at ?? '--:--'}</span> {line.text}
                </li>
              ))}
            </ul>
          </details>
        ))}
        {(tasks.data?.items.length ?? 0) === 0 && (
          <EmptyState title="还没有批次记录" hint="先跑一次采集，账本会记下扫描量、新增/更新与异常条数。" />
        )}
      </div>
    </>
  );
}

import { Fragment, useState } from 'react';
import { Link } from 'react-router-dom';
import ChapterTimeline from '../components/common/ChapterTimeline';
import EmptyState from '../components/common/EmptyState';
import IssueMixBar from '../components/common/IssueMixBar';
import PageHead from '../components/common/PageHead';
import StatusPill from '../components/common/StatusPill';
import TapeLabel from '../components/common/TapeLabel';
import { feedApi, summaryApi } from '../api/feeds';
import { episodeApi } from '../api/episodes';
import { issueApi } from '../api/issues';
import { exportApi } from '../api/exports';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../router/guards';
import { can } from '../constants/roles';
import { ISSUES_HINT } from '../constants/ui';
import { ISSUE_KIND_LABELS, ISSUE_KIND_ORDER, ISSUE_SEVERITY_TONE } from '../constants/enums';
import { errorMessage } from '../utils/errorMessage';
import { uiStore } from '../stores/uiStore';
import type { EpisodeDetail } from '../types/models';

export default function Issues() {
  const state = useAuth();
  const canResolve = can(state.user?.role, 'issue:resolve');

  const [kind, setKind] = useState('');
  const [status, setStatus] = useState('open');
  const [feed, setFeed] = useState('');
  const [busy, setBusy] = useState(false);
  const [timelineCode, setTimelineCode] = useState<string | null>(null);
  const [timelineData, setTimelineData] = useState<EpisodeDetail | null>(null);

  const toggleTimeline = async (code: string) => {
    if (timelineCode === code) {
      setTimelineCode(null);
      return;
    }
    setTimelineCode(code);
    if (timelineData?.episode.code === code) return;
    try {
      const detail = await episodeApi.detail(code);
      setTimelineData(detail);
    } catch (error) {
      uiStore.toast(errorMessage((error as { payload?: unknown })?.payload, '时间轴读取失败'), 'bad');
      setTimelineCode(null);
    }
  };

  const summary = useAsync(() => issueApi.summary(), []);
  const feeds = useAsync(() => feedApi.list(), []);
  const overview = useAsync(() => summaryApi.overview(), []);
  const issues = useAsync(
    () => issueApi.list({ kind: kind || undefined, status: status || undefined, feed: feed || undefined, size: 100 }),
    [kind, status, feed],
  );

  const reloadAll = () => {
    issues.reload();
    summary.reload();
    overview.reload();
  };

  const resolve = async (id: number) => {
    setBusy(true);
    try {
      await issueApi.resolve(id, '异常队列人工确认');
      uiStore.toast('异常已处置');
      reloadAll();
    } catch (error) {
      uiStore.toast(errorMessage((error as { payload?: unknown })?.payload, '处置失败'), 'bad');
    } finally {
      setBusy(false);
    }
  };

  const rescan = async () => {
    setBusy(true);
    try {
      const result = await issueApi.rescan();
      uiStore.toast(`全量复扫 ${result.episodes} 集：待处理 ${result.open}，已处置 ${result.resolved}`);
      reloadAll();
    } catch (error) {
      uiStore.toast(errorMessage((error as { payload?: unknown })?.payload, '复扫失败'), 'bad');
    } finally {
      setBusy(false);
    }
  };

  const download = async (kindName: 'clip' | 'chapter' | 'issuesCsv') => {
    setBusy(true);
    try {
      if (kindName === 'clip') {
        const size = await exportApi.clipList();
        uiStore.toast(`剪辑清单已下载（${Math.round(size / 1024)} KB）`);
      } else if (kindName === 'chapter') {
        const size = await exportApi.chapterCuts();
        uiStore.toast(`章节切点清单已下载（${Math.round(size / 1024)} KB）`);
      } else {
        const size = await exportApi.issues();
        uiStore.toast(`异常清单已下载（${Math.round(size / 1024)} KB）`);
      }
    } catch (error) {
      uiStore.toast(errorMessage((error as { payload?: unknown })?.payload, '导出失败'), 'bad');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHead
        eyebrow="QC QUEUE · 异常队列"
        title="章节异常与剪辑清单"
        lede={ISSUES_HINT}
        meta={
          <>
            <span className="chip mono">{summary.data?.open ?? '—'} 待处理</span>
            <span className="chip mono">{summary.data?.gap ?? '—'} 缺口</span>
            <span className="chip mono">{summary.data?.unparsed ?? '—'} 未识别</span>
            <span className="chip mono">{overview.data?.chapters ?? '—'} 章</span>
          </>
        }
        actions={
          <>
            <button type="button" className="btn btn-primary" disabled={busy} onClick={() => download('clip')}>
              导出剪辑清单 CSV
            </button>
            <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => download('chapter')}>
              章节切点 CSV
            </button>
            <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => download('issuesCsv')}>
              异常清单 CSV
            </button>
          </>
        }
      />

      <section className="issue-summary">
        <div className="issue-mix">
          <TapeLabel eyebrow="MIX · 异常构成" title="待处理分布" tone="plain" />
          <IssueMixBar data={summary.data?.by_kind ?? []} />
        </div>
        <div className="issue-note">
          <TapeLabel eyebrow="RULES · 判定口径" title="五条窗口不变量" tone="plain" />
          <ul className="rule-list">
            <li>
              <b>严格递增</b>：按 show notes 行序，时间点不得小于前文最大值 → 乱序
            </li>
            <li>
              <b>末章 ≤ 时长</b>：任何时间点超出单集时长 → 超时长
            </li>
            <li>
              <b>重叠合并</b>：同一时间点保留置信高者，标题用 / 合并
            </li>
            <li>
              <b>&lt; 20s 折叠</b>：窗口过短的章节折叠进前一章
            </li>
            <li>
              <b>缺口 &gt; 8min</b>：相邻章节空档过大 → 给出建议补章区间
            </li>
          </ul>
          {canResolve && (
            <button type="button" className="btn btn-ghost" disabled={busy} onClick={rescan}>
              全量复扫
            </button>
          )}
        </div>
      </section>

      <TapeLabel
        eyebrow="QUEUE · 工单"
        title="异常清单"
        meta={
          <span className="mono">
            {issues.data?.total ?? 0} 条命中当前筛选
            {!canResolve && ' · 剪辑师只读'}
          </span>
        }
      />

      <div className="filters">
        <label className="field field-inline">
          <span>异常类型</span>
          <select value={kind} onChange={(event) => setKind(event.target.value)}>
            <option value="">全部类型</option>
            {ISSUE_KIND_ORDER.map((item) => (
              <option key={item} value={item}>
                {ISSUE_KIND_LABELS[item]}
              </option>
            ))}
          </select>
        </label>
        <label className="field field-inline">
          <span>处理状态</span>
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">全部</option>
            <option value="open">待处理</option>
            <option value="resolved">已处置</option>
          </select>
        </label>
        <label className="field field-inline">
          <span>节目</span>
          <select value={feed} onChange={(event) => setFeed(event.target.value)}>
            <option value="">全部节目</option>
            {(feeds.data?.items ?? []).map((item) => (
              <option key={item.code} value={item.code}>
                {item.show_name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="btn btn-quiet" onClick={reloadAll}>
          刷新
        </button>
      </div>

      {issues.error ? (
        <EmptyState
          tone="error"
          title="异常队列读不出来"
          hint={errorMessage((issues.error as { payload?: unknown })?.payload, '接口返回异常')}
          actionLabel="重试"
          onAction={issues.reload}
        />
      ) : (issues.data?.items.length ?? 0) === 0 ? (
        <EmptyState
          title="这个筛选下没有异常"
          hint="试试把「处理状态」切到全部，或者去节目库挑一集看看时间轴。"
          actionLabel="看节目库"
          onAction={() => {
            window.location.href = '/library';
          }}
        />
      ) : (
        <div className="table-wrap">
          <table className="data-table issue-table">
            <thead>
              <tr>
                <th>类型</th>
                <th>单集</th>
                <th>位置</th>
                <th>说明</th>
                <th>建议</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {(issues.data?.items ?? []).map((issue) => (
                <Fragment key={issue.id}>
                <tr>
                  <td>
                    <StatusPill tone={ISSUE_SEVERITY_TONE[issue.severity] ?? 'warn'}>{issue.kind_label}</StatusPill>
                  </td>
                  <td>
                    <Link className="table-link" to={`/episodes/${issue.episode_code}`}>
                      <span className="mono">{issue.episode_code}</span>
                      <span className="table-sub">{issue.episode_title}</span>
                    </Link>
                    <span className="table-sub muted">{issue.feed_name}</span>
                  </td>
                  <td className="mono">{issue.chapter_time_tc ?? issue.window_start_tc ?? '—'}</td>
                  <td className="issue-cell">{issue.message}</td>
                  <td className="issue-cell muted">{issue.suggestion}</td>
                  <td>
                    {issue.status === 'open' ? (
                      <StatusPill tone="bad" dot>
                        待处理
                      </StatusPill>
                    ) : (
                      <StatusPill tone="ok">{issue.resolution_note || '已处置'}</StatusPill>
                    )}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-quiet btn-sm"
                      onClick={() => toggleTimeline(issue.episode_code)}
                    >
                      {timelineCode === issue.episode_code ? '收起' : '时间轴'}
                    </button>
                    {canResolve && issue.status === 'open' ? (
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        disabled={busy}
                        onClick={() => resolve(issue.id)}
                      >
                        处置
                      </button>
                    ) : (
                      <span className="muted mono">—</span>
                    )}
                  </td>
                </tr>
                {timelineCode === issue.episode_code && timelineData?.episode.code === issue.episode_code && (
                  <tr className="timeline-row">
                    <td colSpan={7}>
                      <div className="timeline-pop">
                        <div className="timeline-pop-head mono">
                          {issue.episode_code} · {issue.episode_title} · 时长 {timelineData.episode.duration_tc}
                        </div>
                        <ChapterTimeline
                          compact
                          duration={timelineData.episode.duration_seconds}
                          chapters={timelineData.chapters}
                          selectedId={issue.chapter_id}
                        />
                      </div>
                    </td>
                  </tr>
                )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

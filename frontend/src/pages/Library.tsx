import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PageHead from '../components/common/PageHead';
import StatusPill from '../components/common/StatusPill';
import Timecode from '../components/common/Timecode';
import EmptyState from '../components/common/EmptyState';
import { episodeApi } from '../api/episodes';
import { feedApi, summaryApi } from '../api/feeds';
import { useAsync } from '../hooks/useAsync';
import { uiStore } from '../stores/uiStore';
import { LIBRARY_HINT } from '../constants/ui';
import { PARSE_STATUS_LABELS } from '../constants/enums';
import { errorMessage } from '../utils/errorMessage';
import { shortDate } from '../utils/format';
import type { ParseStatus } from '../types/models';

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: '全部状态' },
  { value: 'parsed', label: '已解析' },
  { value: 'partial', label: '部分解析' },
  { value: 'pending', label: '待解析' },
  { value: 'failed', label: '解析失败' },
];

function parseTone(status: ParseStatus) {
  if (status === 'parsed') return 'ok';
  if (status === 'partial') return 'warn';
  if (status === 'failed') return 'bad';
  return 'muted';
}

export default function Library() {
  const navigate = useNavigate();
  const [feedFilter, setFeedFilter] = useState('');
  const [status, setStatus] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);

  const overview = useAsync(() => summaryApi.overview(), []);
  const feeds = useAsync(() => feedApi.list(), []);
  const episodes = useAsync(
    () =>
      episodeApi.list({
        feed: feedFilter || undefined,
        status: status || undefined,
        q: query || undefined,
        page,
        size: 12,
      }),
    [feedFilter, status, query, page],
  );

  const total = episodes.data?.total ?? 0;
  const size = episodes.data?.size ?? 12;
  const pages = Math.max(1, Math.ceil(total / size));

  return (
    <>
      <PageHead
        eyebrow="TAPE LIBRARY · 磁带架"
        title="节目库"
        lede={LIBRARY_HINT}
        meta={
          <>
            <span className="chip mono">{overview.data?.episodes ?? '—'} 集</span>
            <span className="chip mono">{overview.data?.chapters ?? '—'} 章</span>
            <span className="chip mono">{overview.data?.open_issues ?? '—'} 待处理</span>
            <span className="chip mono">{overview.data?.unparsed_chapters ?? '—'} 未识别</span>
          </>
        }
        actions={
          <button type="button" className="btn btn-ghost" onClick={() => { episodes.reload(); overview.reload(); }}>
            刷新
          </button>
        }
      />

      <div className="filters">
        <label className="field field-inline">
          <span>订阅源</span>
          <select
            value={feedFilter}
            onChange={(event) => {
              setFeedFilter(event.target.value);
              uiStore.setFeedFilter(event.target.value);
              setPage(1);
            }}
          >
            <option value="">全部节目</option>
            {(feeds.data?.items ?? []).map((feed) => (
              <option key={feed.code} value={feed.code}>
                {feed.show_name}（{feed.episode_count}）
              </option>
            ))}
          </select>
        </label>

        <label className="field field-inline">
          <span>解析状态</span>
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
          >
            {STATUS_OPTIONS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field field-inline field-grow">
          <span>搜索</span>
          <input
            value={query}
            placeholder="标题 / 单集号 / 节目名"
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
          />
        </label>
      </div>

      {episodes.error ? (
        <EmptyState
          tone="error"
          title="节目库没读出来"
          hint={errorMessage((episodes.error as { payload?: unknown })?.payload, '接口返回异常')}
          actionLabel="重试"
          onAction={episodes.reload}
        />
      ) : episodes.loading && !episodes.data ? (
        <div className="skeleton-table">正在读带 …</div>
      ) : (episodes.data?.items.length ?? 0) === 0 ? (
        <EmptyState
          title="这个筛选条件下没有单集"
          hint="换一个订阅源或清空搜索词；也可以先去「订阅源」页面跑一次采集。"
          actionLabel="去订阅源"
          onAction={() => navigate('/feeds')}
        />
      ) : (
        <>
          <ol className="ep-list">
            {(episodes.data?.items ?? []).map((episode) => (
              <li key={episode.id}>
                <button
                  type="button"
                  className="ep-row"
                  onClick={() => navigate(`/episodes/${episode.code}`)}
                >
                  <span className="ep-cover" aria-hidden>
                    <em>{episode.code.replace('EP-', '')}</em>
                    <i />
                  </span>
                  <span className="ep-main">
                    <span className="ep-kicker mono">
                      {episode.code} · S{episode.season}E{String(episode.episode_no).padStart(2, '0')}
                    </span>
                    <span className="ep-title">{episode.title}</span>
                    <span className="ep-sub">
                      {episode.show_name} · {shortDate(episode.published_on)}
                      {episode.ingest_state === 'pending' && (
                        <StatusPill tone="info" dot>
                          待入库
                        </StatusPill>
                      )}
                    </span>
                  </span>
                  <span className="ep-metrics">
                    <Timecode value={episode.duration_tc} size="sm" />
                    <span className="mono ep-chapters">{episode.chapter_count} 章</span>
                  </span>
                  <span className="ep-status">
                    <StatusPill tone={parseTone(episode.parse_status) as never}>
                      {PARSE_STATUS_LABELS[episode.parse_status] ?? episode.parse_status}
                    </StatusPill>
                    {episode.issue_count > 0 && <StatusPill tone="bad">{episode.issue_count} 异常</StatusPill>}
                    {episode.unparsed_count > 0 && (
                      <StatusPill tone="muted">{episode.unparsed_count} 未识别</StatusPill>
                    )}
                  </span>
                </button>
              </li>
            ))}
          </ol>

          <div className="pager">
            <button
              type="button"
              className="btn btn-ghost"
              disabled={page <= 1}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
            >
              上一盘
            </button>
            <span className="mono">
              {page} / {pages} · 共 {total} 集
            </span>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={page >= pages}
              onClick={() => setPage((value) => Math.min(pages, value + 1))}
            >
              下一盘
            </button>
          </div>
        </>
      )}
    </>
  );
}

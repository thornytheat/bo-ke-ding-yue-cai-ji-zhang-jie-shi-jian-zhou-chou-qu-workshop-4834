import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import ChapterTimeline from '../components/common/ChapterTimeline';
import EmptyState from '../components/common/EmptyState';
import StatusPill from '../components/common/StatusPill';
import TapeLabel from '../components/common/TapeLabel';
import Timecode from '../components/common/Timecode';
import { episodeApi } from '../api/episodes';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../router/guards';
import { can } from '../constants/roles';
import { CHAPTER_SOURCE_LABELS, ISSUE_SEVERITY_TONE, PARSE_RULE_LABELS, PARSE_STATUS_LABELS } from '../constants/enums';
import { uiStore } from '../stores/uiStore';
import { errorMessage } from '../utils/errorMessage';
import { humanDuration, shortDate } from '../utils/format';
import type { Chapter } from '../types/models';

function payloadFor(time: string, title: string, chapter?: Chapter) {
  const payload: { title?: string; raw_text?: string; start_seconds?: number } = { title };
  const trimmed = time.trim();
  if (trimmed && trimmed !== chapter?.start_tc) {
    if (/^\d+$/.test(trimmed)) {
      payload.start_seconds = Number(trimmed);
    } else {
      payload.raw_text = trimmed;
    }
  }
  return payload;
}

export default function EpisodeDetail() {
  const { code = '' } = useParams();
  const state = useAuth();
  const canWrite = can(state.user?.role, 'chapter:write');

  const detail = useAsync(() => episodeApi.detail(code), [code]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draftTime, setDraftTime] = useState('');
  const [draftTitle, setDraftTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [fixNote, setFixNote] = useState<string | null>(null);
  const [newTime, setNewTime] = useState('');
  const [newTitle, setNewTitle] = useState('');

  const data = detail.data;
  const report = (message: string, bad = false) => uiStore.toast(message, bad ? 'bad' : 'ok');

  const guarded = async (task: () => Promise<void>, okMessage: string) => {
    setBusy(true);
    try {
      await task();
      report(okMessage);
      detail.reload();
    } catch (error) {
      report(errorMessage((error as { payload?: unknown })?.payload, '操作失败'), true);
    } finally {
      setBusy(false);
    }
  };

  const startEdit = (chapter: Chapter) => {
    setEditingId(chapter.id);
    setDraftTime(chapter.start_tc ?? chapter.raw_text ?? '');
    setDraftTitle(chapter.title);
  };

  const saveEdit = async (chapter: Chapter) => {
    await guarded(async () => {
      await episodeApi.patchChapter(code, chapter.id, payloadFor(draftTime, draftTitle, chapter));
      setEditingId(null);
    }, '章节已保存并重跑校验');
  };

  if (detail.error) {
    return (
      <EmptyState
        tone="error"
        title="这一集读不出来"
        hint={errorMessage((detail.error as { payload?: unknown })?.payload, '接口返回异常')}
        actionLabel="重试"
        onAction={detail.reload}
      />
    );
  }

  if (!data) {
    return <div className="skeleton-table">正在展开磁带 …</div>;
  }

  const { episode, feed, chapters, notes_lines, issues, validation } = data;
  const selected = chapters.find((chapter) => chapter.id === selectedId) ?? null;

  return (
    <>
      <div className="detail-head">
        <Link className="back-link mono" to="/library">
          ← 节目库
        </Link>
        <div className="detail-title">
          <div className="eyebrow mono">
            {episode.code} · {feed.show_name} · S{episode.season}E{String(episode.episode_no).padStart(2, '0')}
          </div>
          <h1>{episode.title}</h1>
          <div className="detail-meta">
            <span className="chip mono">{episode.duration_tc}</span>
            <span className="chip">{humanDuration(episode.duration_seconds)}</span>
            <span className="chip">{shortDate(episode.published_on)}</span>
            <StatusPill tone={episode.parse_status === 'parsed' ? 'ok' : episode.parse_status === 'partial' ? 'warn' : 'muted'}>
              {PARSE_STATUS_LABELS[episode.parse_status] ?? episode.parse_status}
            </StatusPill>
            <span className="chip mono">{episode.chapter_count} 章</span>
            {episode.issue_count > 0 && <StatusPill tone="bad">{episode.issue_count} 待处理</StatusPill>}
            {!canWrite && <StatusPill tone="muted">只读视图</StatusPill>}
          </div>
        </div>
        {canWrite && (
          <div className="detail-actions">
            <button
              type="button"
              className="btn btn-ghost"
              disabled={busy}
              onClick={() =>
                guarded(async () => {
                  const result = await episodeApi.reparse(code);
                  setFixNote(
                    `重跑解析：${result.entries} 行章节，未识别 ${result.unparsed} 行，歧义 ${result.ambiguous} 条；` +
                      result.about_minutes
                        .map((item) => `「${item.raw}」→ ${item.seconds}s`)
                        .join('，'),
                  );
                }, '已按 show notes 重跑解析')
              }
            >
              重跑解析
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy}
              onClick={() =>
                guarded(async () => {
                  const result = await episodeApi.normalize(code);
                  setFixNote(
                    `不变量修正：乱序重排 ${result.reordered} 条、重叠合并 ${result.merged} 条、` +
                      `过短折叠 ${result.folded} 条、删除重复行 ${result.deleted_rows} 行；` +
                      `剩余待处理异常 ${result.open_issues} 条。`,
                  );
                }, '已应用不变量修正')
              }
            >
              应用不变量修正
            </button>
          </div>
        )}
      </div>

      {fixNote && (
        <div className="fix-note">
          <span className="mono">RESULT</span>
          <p>{fixNote}</p>
          <button type="button" className="btn btn-quiet" onClick={() => setFixNote(null)}>
            收起
          </button>
        </div>
      )}

      <TapeLabel
        eyebrow="TIMELINE · 走带时间轴"
        title={selected ? `${selected.start_tc ?? '未定位'} · ${selected.title}` : '章节标记与缺口'}
        meta={
          <span className="mono">
            缺口告警 {validation.gaps.length} 处 · 重叠告警 {validation.kind_counts.overlap ?? 0} · 乱序{' '}
            {validation.kind_counts.out_of_order ?? 0}
          </span>
        }
      >
        <ChapterTimeline
          duration={episode.duration_seconds}
          chapters={chapters}
          selectedId={selectedId}
          onSelect={(chapter) => setSelectedId(chapter.id)}
        />
      </TapeLabel>

      <div className="detail-grid">
        <section className="detail-main">
          <TapeLabel
            eyebrow="CHAPTERS · 章节表"
            title="时间点 / 标题 / 窗口"
            meta={<span className="mono">{chapters.length} 行 · 窗口 &lt; 20s 折叠、缺口 &gt; 8min 告警</span>}
            actions={
              canWrite ? (
                <button type="button" className="btn btn-ghost" onClick={() => setEditingId(-1)}>
                  新增章节
                </button>
              ) : null
            }
          />

          <div className="table-wrap">
            <table className="data-table chapter-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>时间点</th>
                  <th>标题</th>
                  <th>窗口</th>
                  <th>来源</th>
                  <th>置信</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {chapters.map((chapter) => {
                  const isEditing = editingId === chapter.id;
                  if (isEditing) {
                    return (
                      <tr key={chapter.id} className="row-editing">
                        <td className="mono">{chapter.ordinal + 1}</td>
                        <td>
                          <input
                            className="input tc"
                            value={draftTime}
                            placeholder="01:23 / 1:02:30 / 1分23秒"
                            onChange={(event) => setDraftTime(event.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            className="input"
                            value={draftTitle}
                            onChange={(event) => setDraftTitle(event.target.value)}
                          />
                        </td>
                        <td colSpan={3} className="muted">
                          保存后后端会重新解析时间码并跑一次不变量校验
                        </td>
                        <td>
                          <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={() => saveEdit(chapter)}>
                            保存
                          </button>
                          <button type="button" className="btn btn-quiet btn-sm" onClick={() => setEditingId(null)}>
                            取消
                          </button>
                        </td>
                      </tr>
                    );
                  }
                  return (
                    <tr
                      key={chapter.id}
                      className={selectedId === chapter.id ? 'row-active' : ''}
                      onClick={() => setSelectedId(chapter.id)}
                    >
                      <td className="mono">{chapter.ordinal + 1}</td>
                      <td>
                        {chapter.start_seconds === null ? (
                          <span className="tc tc-muted">--:--</span>
                        ) : (
                          <Timecode value={chapter.start_tc} />
                        )}
                        {chapter.ambiguous && (
                          <StatusPill tone="warn" title="裸 M:SS 在该时长下也能读成 H:MM">
                            歧义
                          </StatusPill>
                        )}
                      </td>
                      <td>
                        <span className="chapter-title">{chapter.title}</span>
                        {chapter.auto_fixed && chapter.fix_note && (
                          <span className="fix-tag mono">{chapter.fix_note}</span>
                        )}
                      </td>
                      <td className="mono muted">{chapter.window_human}</td>
                      <td>
                        <StatusPill
                          tone={
                            chapter.source === 'manual' ? 'tape' : chapter.source === 'unparsed' ? 'bad' : 'muted'
                          }
                        >
                          {CHAPTER_SOURCE_LABELS[chapter.source] ?? chapter.source}
                        </StatusPill>
                        <span className="rule mono">{PARSE_RULE_LABELS[chapter.parse_rule] ?? chapter.parse_rule}</span>
                      </td>
                      <td className="mono">{chapter.confidence ? chapter.confidence.toFixed(2) : '—'}</td>
                      <td>
                        {canWrite ? (
                          <>
                            <button
                              type="button"
                              className="btn btn-quiet btn-sm"
                              onClick={(event) => {
                                event.stopPropagation();
                                startEdit(chapter);
                              }}
                            >
                              {chapter.start_seconds === null ? '补时间点' : '编辑'}
                            </button>
                            <button
                              type="button"
                              className="btn btn-danger btn-sm"
                              onClick={(event) => {
                                event.stopPropagation();
                                if (window.confirm(`删除章节「${chapter.title}」？`)) {
                                  guarded(async () => {
                                    await episodeApi.deleteChapter(code, chapter.id);
                                  }, '章节已删除');
                                }
                              }}
                            >
                              删除
                            </button>
                          </>
                        ) : (
                          <span className="muted mono">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}

                {canWrite && editingId === -1 && (
                  <tr className="row-editing">
                    <td className="mono">新</td>
                    <td>
                      <input
                        className="input tc"
                        value={newTime}
                        placeholder="01:23 或 720"
                        onChange={(event) => setNewTime(event.target.value)}
                      />
                    </td>
                    <td>
                      <input className="input" value={newTitle} onChange={(event) => setNewTitle(event.target.value)} />
                    </td>
                    <td colSpan={3} className="muted">
                      人工补录的章节来源会标为「人工补录」，置信度 1.00
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        disabled={busy}
                        onClick={() =>
                          guarded(async () => {
                            await episodeApi.addChapter(code, {
                              ...payloadFor(newTime, newTitle || '未命名章节'),
                            });
                            setEditingId(null);
                            setNewTime('');
                            setNewTitle('');
                          }, '章节已新增')
                        }
                      >
                        保存
                      </button>
                      <button type="button" className="btn btn-quiet btn-sm" onClick={() => setEditingId(null)}>
                        取消
                      </button>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="detail-side">
          <TapeLabel
            eyebrow="SOURCE · show notes 原文"
            title="逐行对照"
            meta={<span className="mono">{notes_lines.length} 行 · 灰=正文，橙=已识别，红=未识别</span>}
            tone="plain"
          />

          <div className="notes">
            {notes_lines.map((line) => (
              <div key={line.line_no} className={`note-line note-${line.state}`}>
                <span className="note-no mono">{String(line.line_no).padStart(2, '0')}</span>
                <span className="note-text">{line.text || '\u00a0'}</span>
                {line.state === 'parsed' && (
                  <span className="note-tc mono" title={PARSE_RULE_LABELS[line.rule ?? ''] ?? line.rule}>
                    {line.time_tc}
                  </span>
                )}
                {line.state === 'unparsed' && <span className="note-tc bad mono">未识别</span>}
              </div>
            ))}
          </div>

          <TapeLabel
            eyebrow="ISSUES · 校验结论"
            title={issues.length ? `${issues.length} 条待处理` : '本集没有待处理异常'}
            tone="plain"
          />
          <ul className="issue-list">
            {issues.length === 0 && <li className="issue-empty muted">窗口不变量全部通过。</li>}
            {issues.map((issue) => (
              <li key={issue.id} className="issue-item">
                <div className="issue-head">
                  <StatusPill tone={ISSUE_SEVERITY_TONE[issue.severity] ?? 'warn'}>
                    {issue.kind_label}
                  </StatusPill>
                  {issue.window_start_tc && <span className="mono muted">{issue.window_start_tc}</span>}
                </div>
                <p className="issue-msg">{issue.message}</p>
                <p className="issue-fix">建议：{issue.suggestion}</p>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </>
  );
}

export type Role = 'admin' | 'analyst' | 'viewer';

export interface UserInfo {
  id: number;
  email: string;
  display_name: string;
  role: Role;
  role_label: string;
  permissions: string[];
}

export interface Feed {
  id: number;
  code: string;
  name: string;
  show_name: string;
  kind: FeedKind;
  kind_label: string;
  url: string;
  fixture_path: string;
  cadence: string;
  host: string;
  active: boolean;
  last_fetch_at: string | null;
  last_status: string;
  last_episode_count: number;
  note: string;
  episode_count: number;
  chapter_count: number;
  open_issues: number;
  pending_episodes: number;
}

export type FeedKind = 'rss' | 'platform' | 'apple';

export interface EpisodeBrief {
  id: number;
  code: string;
  title: string;
  feed_code: string;
  feed_name: string;
  show_name: string;
  season: number;
  episode_no: number;
  duration_seconds: number;
  duration_tc: string;
  published_on: string | null;
  summary: string;
  cover_hint: string;
  ingest_state: 'pending' | 'synced';
  parse_status: ParseStatus;
  parse_status_label: string;
  chapter_count: number;
  unparsed_count: number;
  issue_count: number;
  parsed_at: string | null;
}

export type ParseStatus = 'pending' | 'parsed' | 'partial' | 'failed';

export interface Chapter {
  id: number;
  ordinal: number;
  start_seconds: number | null;
  start_tc: string | null;
  start_full_tc: string | null;
  title: string;
  raw_text: string;
  parse_rule: string;
  confidence: number;
  ambiguous: boolean;
  source: ChapterSource;
  source_label: string;
  auto_fixed: boolean;
  fix_note: string;
  window_seconds: number | null;
  window_human: string;
}

export type ChapterSource = 'parse' | 'manual' | 'unparsed';

export interface NoteLine {
  line_no: number;
  text: string;
  state: 'parsed' | 'unparsed' | 'ignored';
  seconds?: number | null;
  time_tc?: string | null;
  title?: string;
  rule?: string;
  confidence?: number;
  ambiguous?: boolean;
}

export type IssueKind =
  | 'out_of_order'
  | 'overlap'
  | 'over_duration'
  | 'too_short'
  | 'gap_warning'
  | 'unparsed';

export interface IssueItem {
  id: number;
  issue_key: string;
  kind: IssueKind;
  kind_label: string;
  status: 'open' | 'resolved';
  severity: string;
  message: string;
  suggestion: string;
  window_start: number | null;
  window_end: number | null;
  window_start_tc: string | null;
  episode_code: string;
  episode_id: number;
  episode_title: string;
  feed_code: string;
  feed_name: string;
  chapter_id: number | null;
  chapter_title: string;
  chapter_time_tc: string | null;
  resolved_by: string;
  resolution_note: string;
  created_at: string | null;
}

export interface IssueSummary {
  open: number;
  resolved: number;
  total: number;
  gap: number;
  unparsed: number;
  by_kind: { kind: IssueKind; label: string; open: number; resolved: number; total: number }[];
}

export interface TaskLogLine {
  level: string;
  text: string;
  at?: string;
}

export interface TaskItem {
  id: number;
  code: string;
  mode: 'ingest' | 'parse' | 'both';
  mode_label: string;
  status: 'queued' | 'running' | 'success' | 'failed';
  status_label: string;
  feed_scope: string;
  triggered_by: string;
  triggered_role: string;
  feeds_scanned: number;
  episodes_scanned: number;
  episodes_new: number;
  episodes_updated: number;
  episodes_unchanged: number;
  chapters_parsed: number;
  unparsed_chapters: number;
  issues_found: number;
  duration_ms: number;
  log_lines: TaskLogLine[];
  error_text: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
}

export interface EpisodeDetail {
  episode: EpisodeBrief;
  feed: { code: string; name: string; show_name: string; kind: FeedKind; host: string; cadence: string };
  chapters: Chapter[];
  show_notes: string;
  notes_lines: NoteLine[];
  issues: {
    id: number;
    kind: IssueKind;
    kind_label: string;
    status: string;
    severity: string;
    message: string;
    suggestion: string;
    window_start_tc: string | null;
    resolution_note: string;
  }[];
  validation: {
    reordered: number;
    merged: number;
    folded: number;
    gaps: { issue_key: string; gap_seconds: number; suggestion_start: number; suggestion_end: number }[];
    issue_count: number;
    kind_counts: Record<string, number>;
  };
}

export interface Overview {
  feeds: number;
  active_feeds: number;
  episodes: number;
  chapters: number;
  unparsed_chapters: number;
  ambiguous_chapters: number;
  pending_ingest: number;
  partial_parse: number;
  open_issues: number;
  resolved_issues: number;
  total_issues: number;
  gap_issues: number;
  running_tasks: number;
  issues_by_kind: { kind: IssueKind; label: string; open: number; resolved: number; total: number }[];
  latest_task: {
    code: string;
    mode: string;
    status: string;
    finished_at: string | null;
    episodes_scanned: number;
    chapters_parsed: number;
    issues_found: number;
  } | null;
}

export interface FeedPreview {
  feed: Feed;
  scanned: number;
  created: { guid: string; title: string; published_on: string; episode_code?: string; reason?: string }[];
  updated: { guid: string; episode_code: string; title: string; changes: { field: string; from: unknown; to: unknown }[] }[];
  unchanged: number;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

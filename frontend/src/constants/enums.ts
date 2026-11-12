/** 共享枚举（前端副本）。后端唯一定义处：backend/src/constants/enums.py */
import type { ChapterSource, FeedKind, IssueKind, ParseStatus, Role } from '../types/models';

export const ROLE_LABELS: Record<Role, string> = {
  admin: '运营主管',
  analyst: '内容运营',
  viewer: '剪辑师（只读）',
};

export const FEED_KIND_LABELS: Record<FeedKind, string> = {
  rss: 'RSS 订阅',
  platform: '平台接口',
  apple: '目录 HTML',
};

export const PARSE_STATUS_LABELS: Record<ParseStatus, string> = {
  pending: '待解析',
  parsed: '已解析',
  partial: '部分解析',
  failed: '解析失败',
};

export const CHAPTER_SOURCE_LABELS: Record<ChapterSource, string> = {
  parse: '自动解析',
  manual: '人工补录',
  unparsed: '未识别',
};

export const ISSUE_KIND_LABELS: Record<IssueKind, string> = {
  out_of_order: '乱序',
  overlap: '重叠',
  over_duration: '超时长',
  too_short: '过短折叠',
  gap_warning: '缺口告警',
  unparsed: '未识别',
};

/** 异常队列展示顺序：越靠前越影响切片 */
export const ISSUE_KIND_ORDER: IssueKind[] = [
  'out_of_order',
  'overlap',
  'over_duration',
  'too_short',
  'gap_warning',
  'unparsed',
];

export const ISSUE_SEVERITY_CLASS: Record<string, string> = {
  block: 'pill bad',
  warn: 'pill warn',
  info: 'pill muted',
};

/** 严重度 -> StatusPill tone（block 红 / warn 黄 / info 灰） */
export const ISSUE_SEVERITY_TONE: Record<string, 'bad' | 'warn' | 'muted'> = {
  block: 'bad',
  warn: 'warn',
  info: 'muted',
};

export const TASK_STATUS_LABELS: Record<string, string> = {
  queued: '排队中',
  running: '运行中',
  success: '成功',
  failed: '失败',
};

export const TASK_MODE_LABELS: Record<string, string> = {
  ingest: '采集',
  parse: '解析',
  both: '采集 + 解析',
};

export const PARSE_RULE_LABELS: Record<string, string> = {
  hh_mm_ss: 'hh:mm:ss',
  mm_ss: 'mm:ss',
  cn_hour: 'X时Y分Z秒',
  cn_minute: 'X分Y秒',
  about_minutes: '约 N 分钟处',
  at_mmss: '@mm:ss',
  unrecognized: '未识别',
  manual: '人工',
};

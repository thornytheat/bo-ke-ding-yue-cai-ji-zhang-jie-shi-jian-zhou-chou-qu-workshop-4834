const FALLBACK: Record<string, string> = {
  AUTH_INVALID: '邮箱或密码不正确',
  AUTH_MISSING: '登录已过期，请重新登录',
  FORBIDDEN: '当前角色无权执行该操作（服务端返回 403）',
  NOT_FOUND: '对象不存在',
  CONFLICT: '对象状态冲突',
  RATE_LIMITED: '请求过于频繁，请稍后再试',
  VALIDATION: '请求参数不合法',
  EPISODE_LOCKED: '该单集正在被采集任务占用，稍后再试',
  CHAPTER_NOT_FOUND: '章节不存在',
  CHAPTER_OUT_OF_RANGE: '时间点超出单集时长',
  CHAPTER_DUPLICATE: '同一时间点已存在章节',
  TASK_BUSY: '已有采集/解析批次在运行，请等待完成',
  FEED_INACTIVE: '订阅源已停用，无法运行采集',
  EXPORT_EMPTY: '没有可导出的数据',
  INTERNAL: '服务内部错误',
};

export function errorMessage(payload: unknown, fallback = '操作失败'): string {
  if (typeof payload === 'string' && payload) return payload;
  if (payload && typeof payload === 'object') {
    const data = payload as { code?: string; message?: string; detail?: unknown };
    if (data.code && FALLBACK[data.code]) {
      const extra = renderDetail(data.detail);
      return extra ? `${FALLBACK[data.code]} · ${extra}` : FALLBACK[data.code];
    }
    if (data.message) return String(data.message);
  }
  return fallback;
}

function renderDetail(detail: unknown): string {
  if (!detail) return '';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.slice(0, 3).join('; ');
  if (typeof detail === 'object') {
    const map = detail as Record<string, unknown>;
    if (Array.isArray(map.unknown_feeds)) return `未知订阅源: ${(map.unknown_feeds as string[]).join(', ')}`;
    if (Array.isArray(map.inactive_feeds)) return `已停用: ${(map.inactive_feeds as string[]).join(', ')}`;
    if (typeof map.detail === 'string') return map.detail;
    if (typeof map.msg === 'string') return map.msg;
  }
  return '';
}

export function toTimecode(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '--:--:--';
  const value = Math.max(0, Math.round(seconds));
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const secs = value % 60;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export function toShortTimecode(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '--:--';
  const value = Math.max(0, Math.round(seconds));
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const secs = value % 60;
  if (hours) return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export function humanDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—';
  const value = Math.max(0, Math.round(seconds));
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  if (hours) return `${hours}h${String(minutes).padStart(2, '0')}m`;
  return `${minutes}m${String(value % 60).padStart(2, '0')}s`;
}

export function shortDate(value: string | null | undefined): string {
  if (!value) return '—';
  return value.slice(0, 10);
}

export function pct(part: number, total: number): string {
  if (!total) return '0%';
  return `${Math.round((part / total) * 1000) / 10}%`;
}

export function relativeTime(value: string | null | undefined): string {
  if (!value) return '—';
  const stamp = new Date(value.replace(' ', 'T')).getTime();
  if (Number.isNaN(stamp)) return value;
  const diff = Date.now() - stamp;
  if (diff < 0) return value.slice(5, 16);
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} 天前`;
  return value.slice(0, 10);
}

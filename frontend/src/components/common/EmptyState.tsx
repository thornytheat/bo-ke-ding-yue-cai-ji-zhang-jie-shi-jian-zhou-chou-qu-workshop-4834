import ReelMark from './ReelMark';

interface EmptyStateProps {
  title: string;
  hint?: string;
  actionLabel?: string;
  onAction?: () => void;
  tone?: 'idle' | 'error';
}

/** 空态 / 错误态：永远给出下一步，而不是一句「暂无数据」。 */
export default function EmptyState({ title, hint, actionLabel, onAction, tone = 'idle' }: EmptyStateProps) {
  return (
    <div className={`empty empty-${tone}`} role={tone === 'error' ? 'alert' : undefined}>
      <ReelMark size={54} tone="cream" />
      <div>
        <p className="empty-title">{title}</p>
        {hint && <p className="empty-hint">{hint}</p>}
        {actionLabel && onAction && (
          <button type="button" className="btn btn-ghost" onClick={onAction}>
            {actionLabel}
          </button>
        )}
      </div>
    </div>
  );
}

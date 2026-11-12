import type { ReactNode } from 'react';

export type PillTone = 'ok' | 'warn' | 'bad' | 'muted' | 'tape' | 'info';

interface StatusPillProps {
  tone?: PillTone;
  children: ReactNode;
  title?: string;
  dot?: boolean;
}

/** 状态胶囊：所有页面共用（章节来源、解析状态、异常等级、批次状态）。 */
export default function StatusPill({ tone = 'muted', children, title, dot = false }: StatusPillProps) {
  return (
    <span className={`pill pill-${tone}`} title={title}>
      {dot && <i className="pill-dot" aria-hidden />}
      {children}
    </span>
  );
}

import type { ReactNode } from 'react';

interface TapeLabelProps {
  eyebrow?: string;
  title: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
  tone?: 'tape' | 'plain';
  children?: ReactNode;
}

/** 磁带标签样式的区块标题：打孔 + 橙色贴条，替代通用卡片头。 */
export default function TapeLabel({ eyebrow, title, meta, actions, tone = 'tape', children }: TapeLabelProps) {
  return (
    <div className={`tape-label tape-${tone}`}>
      <span className="tape-holes" aria-hidden>
        <i />
        <i />
        <i />
      </span>
      <div className="tape-body">
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h2 className="tape-title">{title}</h2>
        {meta && <div className="tape-meta">{meta}</div>}
      </div>
      {actions && <div className="tape-actions">{actions}</div>}
      {children && <div className="tape-children">{children}</div>}
    </div>
  );
}

import type { ReactNode } from 'react';

interface PageHeadProps {
  eyebrow: string;
  title: string;
  lede?: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
}

export default function PageHead({ eyebrow, title, lede, meta, actions }: PageHeadProps) {
  return (
    <header className="pagehead">
      <div className="pagehead-text">
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {lede && <p className="pagehead-lede">{lede}</p>}
      </div>
      <div className="pagehead-side">
        {meta && <div className="pagehead-meta">{meta}</div>}
        {actions && <div className="pagehead-actions">{actions}</div>}
      </div>
    </header>
  );
}

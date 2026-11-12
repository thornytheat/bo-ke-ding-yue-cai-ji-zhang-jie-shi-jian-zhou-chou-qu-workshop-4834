import type { IssueKind } from '../../types/models';

interface IssueMixBarProps {
  data: { kind: IssueKind; label: string; open: number; resolved: number; total: number }[];
  size?: number;
}

const KIND_COLOR: Record<string, string> = {
  out_of_order: 'oklch(0.72 0.165 55)',
  overlap: 'oklch(0.62 0.19 28)',
  over_duration: 'oklch(0.78 0.14 88)',
  too_short: 'oklch(0.66 0.09 205)',
  gap_warning: 'oklch(0.74 0.11 145)',
  unparsed: 'oklch(0.58 0.02 70)',
};

/** 异常构成环图：SVG 自绘（stroke-dasharray 分段），悬停给出条数。 */
export default function IssueMixBar({ data, size = 132 }: IssueMixBarProps) {
  const rows = data.filter((row) => row.open > 0);
  const total = rows.reduce((sum, row) => sum + row.open, 0);
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <div className="mix">
      <svg width={size} height={size} viewBox="0 0 120 120" role="img" aria-label="异常构成">
        <circle cx="60" cy="60" r={radius} className="mix-track" />
        {total === 0 && <circle cx="60" cy="60" r={radius} className="mix-empty" />}
        {rows.map((row) => {
          const length = (row.open / total) * circumference;
          const dash = `${Math.max(0, length - 2)} ${circumference - Math.max(0, length - 2)}`;
          const circle = (
            <circle
              key={row.kind}
              cx="60"
              cy="60"
              r={radius}
              className="mix-seg"
              stroke={KIND_COLOR[row.kind] ?? 'oklch(0.7 0.05 60)'}
              strokeDasharray={dash}
              strokeDashoffset={-offset}
              transform="rotate(-90 60 60)"
            >
              <title>{`${row.label} ${row.open} 条`}</title>
            </circle>
          );
          offset += length;
          return circle;
        })}
        <text x="60" y="56" className="mix-total">
          {total}
        </text>
        <text x="60" y="72" className="mix-caption">
          待处理
        </text>
      </svg>
      <ul className="mix-legend">
        {data.map((row) => (
          <li key={row.kind} className={row.open ? '' : 'is-zero'}>
            <i style={{ background: KIND_COLOR[row.kind] ?? 'oklch(0.7 0.05 60)' }} />
            <span>{row.label}</span>
            <b className="mono">{row.open}</b>
            <em className="mono">/{row.total}</em>
          </li>
        ))}
      </ul>
    </div>
  );
}

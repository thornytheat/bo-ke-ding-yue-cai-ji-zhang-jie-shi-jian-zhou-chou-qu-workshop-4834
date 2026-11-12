interface ReelMarkProps {
  size?: number;
  spinning?: boolean;
  tone?: 'tape' | 'cream';
}

/** 磁带盘（reel）：走带时旋转，纯 SVG，无外部资源。 */
export default function ReelMark({ size = 56, spinning = false, tone = 'tape' }: ReelMarkProps) {
  const spoke = (angle: number) => {
    const rad = (angle * Math.PI) / 180;
    return {
      x1: 50 + Math.cos(rad) * 14,
      y1: 50 + Math.sin(rad) * 14,
      x2: 50 + Math.cos(rad) * 31,
      y2: 50 + Math.sin(rad) * 31,
    };
  };
  return (
    <svg
      className={`reel ${spinning ? 'reel-spin' : ''}`}
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role="img"
      aria-label="磁带盘"
    >
      <circle cx="50" cy="50" r="47" className={`reel-rim ${tone}`} />
      <circle cx="50" cy="50" r="37" className={`reel-tape ${tone}`} />
      <g className="reel-spokes">
        {[0, 60, 120, 180, 240, 300].map((angle) => {
          const line = spoke(angle);
          return <line key={angle} {...line} className={`reel-spoke ${tone}`} />;
        })}
      </g>
      <circle cx="50" cy="50" r="13" className={`reel-hub ${tone}`} />
      <circle cx="50" cy="50" r="4" className={`reel-hole ${tone}`} />
    </svg>
  );
}

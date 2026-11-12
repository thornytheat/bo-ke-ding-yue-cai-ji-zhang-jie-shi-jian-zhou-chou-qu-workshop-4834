interface TimecodeProps {
  value: string | null | undefined;
  muted?: boolean;
  size?: 'sm' | 'md' | 'lg';
  title?: string;
}

/** 等宽时间码：录音棚里所有时间点都用同一个字形。 */
export default function Timecode({ value, muted = false, size = 'md', title }: TimecodeProps) {
  return (
    <span className={`tc tc-${size} ${muted ? 'tc-muted' : ''}`} title={title}>
      {value ?? '--:--'}
    </span>
  );
}

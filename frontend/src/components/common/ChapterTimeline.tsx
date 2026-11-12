import { toShortTimecode } from '../../utils/format';
import type { Chapter } from '../../types/models';

interface ChapterTimelineProps {
  duration: number;
  chapters: Chapter[];
  selectedId?: number | null;
  onSelect?: (chapter: Chapter) => void;
  compact?: boolean;
}

function tickInterval(duration: number): number {
  if (duration <= 900) return 120;
  if (duration <= 2700) return 300;
  if (duration <= 4200) return 300;
  return 600;
}

/** 走带时间轴：刻度 + 章节标记 + 未识别提示。整块自绘（CSS 刻度 + DOM 标记），不依赖图表库。 */
export default function ChapterTimeline({
  duration,
  chapters,
  selectedId,
  onSelect,
  compact = false,
}: ChapterTimelineProps) {
  const located = chapters.filter((chapter) => chapter.start_seconds !== null);
  const unparsed = chapters.filter((chapter) => chapter.start_seconds === null);
  const interval = tickInterval(duration || 1);
  const ticks: number[] = [];
  for (let seconds = 0; seconds <= duration; seconds += interval) ticks.push(seconds);

  const span = Math.max(1, duration);

  return (
    <div className={`timeline ${compact ? 'timeline-compact' : ''}`}>
      <div className="timeline-ruler" aria-hidden>
        {ticks.map((seconds) => (
          <span key={seconds} className="tick" style={{ left: `${(seconds / span) * 100}%` }}>
            <i />
            <em>{toShortTimecode(seconds)}</em>
          </span>
        ))}
      </div>
      <div className="timeline-track">
        {located.map((chapter) => (
          <button
            key={chapter.id}
            type="button"
            className={`chapter-mark ${selectedId === chapter.id ? 'is-active' : ''} ${
              chapter.source === 'manual' ? 'is-manual' : ''
            } ${chapter.ambiguous ? 'is-ambiguous' : ''}`}
            style={{ left: `${((chapter.start_seconds ?? 0) / span) * 100}%` }}
            onClick={() => onSelect?.(chapter)}
            title={`${toShortTimecode(chapter.start_seconds)} · ${chapter.title}（${chapter.source_label}，置信 ${chapter.confidence}）`}
          >
            <i />
            <span className="mark-time">{toShortTimecode(chapter.start_seconds)}</span>
          </button>
        ))}
      </div>
      <div className="timeline-foot">
        <span className="mono">{located.length} 个时间点</span>
        <span className="mono">时长 {toShortTimecode(duration)}</span>
        {unparsed.length > 0 && (
          <span className="timeline-unparsed" title="这些行的时间码没有被识别，不参与时间轴定位">
            {unparsed.length} 条未定位
          </span>
        )}
      </div>
    </div>
  );
}

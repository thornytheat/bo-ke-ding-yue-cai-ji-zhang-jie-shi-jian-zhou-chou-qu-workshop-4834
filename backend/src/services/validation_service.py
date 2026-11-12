"""章节窗口不变量校验（算法 2，纯函数、无 DB、无随机）。

五条不变量：
  1. 严格递增 —— 按 show notes 行序，时间点不得小于此前最大值（out_of_order）
  2. 末章 ≤ 时长 —— 任何时间点超出单集时长即 over_duration
  3. 重叠合并 —— 同一时间点（容差内）保留置信高者，标题合并
  4. < 20s 折叠 —— 相邻窗口短于 20 秒的章节折叠进前一章（too_short）
  5. 缺口 > 8min —— 相邻章节之间空档过大 → gap_warning，并给建议补章区间

校验不改原文，只产出 issues + 一份「修正后的章节表」（auto_fixed 标记）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.constants.enums import ChapterSource, IssueKind
from src.constants.limits import (
    GAP_WARNING_SECONDS,
    OVERLAP_TOLERANCE_SECONDS,
    SHORT_CHAPTER_SECONDS,
)
from src.utils.timecode import to_short_timecode


@dataclass
class ChapterInput:
    id: int | None
    ordinal: int
    start_seconds: int | None
    title: str
    confidence: float
    source: str
    raw_text: str = ""

    @property
    def ident(self) -> str:
        return str(self.id) if self.id is not None else f"ord{self.ordinal}"


@dataclass
class IssueDraft:
    kind: str
    issue_key: str
    chapter_id: int | None
    message: str
    suggestion: str
    severity: str = "warn"
    window_start: int | None = None
    window_end: int | None = None


@dataclass
class CorrectedChapter:
    chapter_id: int | None
    start_seconds: int
    title: str
    confidence: float
    source: str
    auto_fixed: bool = False
    fix_note: str = ""
    merged_from: list[int] = field(default_factory=list)


@dataclass
class ValidationResult:
    issues: list[IssueDraft] = field(default_factory=list)
    corrected: list[CorrectedChapter] = field(default_factory=list)
    reordered: int = 0
    merged: int = 0
    folded: int = 0
    gaps: list[dict] = field(default_factory=list)
    unparsed: int = 0

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def kind_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.kind] = counts.get(issue.kind, 0) + 1
        return counts

    def to_plan(self) -> dict:
        """给前端「应用修正」按钮用的差异摘要。"""
        return {
            "reordered": self.reordered,
            "merged": self.merged,
            "folded": self.folded,
            "gaps": self.gaps,
            "issue_count": self.issue_count,
            "kind_counts": self.kind_counts(),
        }


def validate_episode(
    episode_code: str,
    duration_seconds: int,
    chapters: list[ChapterInput],
) -> ValidationResult:
    result = ValidationResult()

    # ---- 1) 未识别时间码 ----
    parsed: list[ChapterInput] = []
    for chapter in chapters:
        if chapter.start_seconds is None:
            result.unparsed += 1
            result.issues.append(
                IssueDraft(
                    kind=IssueKind.UNPARSED.value,
                    issue_key=f"{episode_code}:unparsed:{chapter.ident}",
                    chapter_id=chapter.id,
                    message=f"时间码未识别：「{chapter.raw_text or chapter.title}」",
                    suggestion="按 mm:ss 或 hh:mm:ss 补录时间点，再重跑解析",
                    severity="block",
                )
            )
        else:
            parsed.append(chapter)

    if not parsed:
        result.issues.append(
            IssueDraft(
                kind=IssueKind.UNPARSED.value,
                issue_key=f"{episode_code}:unparsed:all",
                chapter_id=None,
                message="整集没有一个可识别的时间码",
                suggestion="检查 show notes 是否有章节段落，或改为人工补录",
                severity="block",
            )
        )
        return result

    # ---- 2) 严格递增（按行序，与最大值比较） ----
    running_max = -1
    for chapter in parsed:
        assert chapter.start_seconds is not None
        if chapter.start_seconds < running_max:
            result.reordered += 1
            result.issues.append(
                IssueDraft(
                    kind=IssueKind.OUT_OF_ORDER.value,
                    issue_key=f"{episode_code}:out_of_order:{chapter.ident}",
                    chapter_id=chapter.id,
                    message=(
                        f"第 {chapter.ordinal + 1} 行时间点 {to_short_timecode(chapter.start_seconds)} "
                        f"小于前文最大时间点 {to_short_timecode(running_max)}"
                    ),
                    suggestion="按时间点重排；重排后请复核该段标题归属",
                    severity="warn",
                    window_start=chapter.start_seconds,
                )
            )
        running_max = max(running_max, chapter.start_seconds)

    # ---- 3) 重叠合并（同一时间点，容差内） ----
    ordered = sorted(parsed, key=lambda row: (row.start_seconds or 0, row.ordinal))
    merged_rows: list[CorrectedChapter] = []
    index = 0
    while index < len(ordered):
        head = ordered[index]
        start = int(head.start_seconds or 0)
        group = [head]
        cursor = index + 1
        while cursor < len(ordered) and abs(int(ordered[cursor].start_seconds or 0) - start) <= OVERLAP_TOLERANCE_SECONDS:
            group.append(ordered[cursor])
            cursor += 1

        if len(group) > 1:
            result.merged += len(group) - 1
            keeper = max(group, key=lambda row: (row.confidence, -row.ordinal))
            titles: list[str] = []
            for row in group:
                if row.title and row.title not in titles:
                    titles.append(row.title)
            merged_title = " / ".join(titles)
            result.issues.append(
                IssueDraft(
                    kind=IssueKind.OVERLAP.value,
                    issue_key=f"{episode_code}:overlap:{start}:{'-'.join(sorted(row.ident for row in group))}",
                    chapter_id=keeper.id,
                    message=(
                        f"{len(group)} 个章节挤在同一时间点 {to_short_timecode(start)}："
                        + "、".join(row.title for row in group)
                    ),
                    suggestion="保留置信高者并合并标题（合并后标题用 / 分隔）",
                    severity="warn",
                    window_start=start,
                    window_end=start,
                )
            )
            merged_rows.append(
                CorrectedChapter(
                    chapter_id=keeper.id,
                    start_seconds=start,
                    title=merged_title[:200],
                    confidence=max(row.confidence for row in group),
                    source=keeper.source,
                    auto_fixed=True,
                    fix_note=f"重叠合并：{len(group)} 条",
                    merged_from=[row.id for row in group if row.id is not None],
                )
            )
        else:
            merged_rows.append(
                CorrectedChapter(
                    chapter_id=head.id,
                    start_seconds=start,
                    title=head.title,
                    confidence=head.confidence,
                    source=head.source,
                )
            )
        index = cursor

    # ---- 4) 超时长 ----
    for row in merged_rows:
        if row.start_seconds > duration_seconds:
            result.issues.append(
                IssueDraft(
                    kind=IssueKind.OVER_DURATION.value,
                    issue_key=f"{episode_code}:over_duration:{row.chapter_id or row.start_seconds}",
                    chapter_id=row.chapter_id,
                    message=(
                        f"时间点 {to_short_timecode(row.start_seconds)} 超出单集时长 "
                        f"{to_short_timecode(duration_seconds)}"
                    ),
                    suggestion="核对时长字段或该章节时间点，必要时下架该章节",
                    severity="block",
                    window_start=row.start_seconds,
                    window_end=duration_seconds,
                )
            )

    # ---- 5) 过短折叠（< 20s 折叠进前一章） ----
    folded_rows: list[CorrectedChapter] = []
    for row in merged_rows:
        if not folded_rows:
            folded_rows.append(row)
            continue
        window = row.start_seconds - folded_rows[-1].start_seconds
        if 0 <= window < SHORT_CHAPTER_SECONDS:
            result.folded += 1
            previous = folded_rows[-1]
            previous.title = f"{previous.title} / {row.title}"[:200]
            previous.auto_fixed = True
            previous.fix_note = (previous.fix_note + "；过短折叠") if previous.fix_note else "过短折叠"
            result.issues.append(
                IssueDraft(
                    kind=IssueKind.TOO_SHORT.value,
                    issue_key=f"{episode_code}:too_short:{row.chapter_id or row.start_seconds}",
                    chapter_id=row.chapter_id,
                    message=(
                        f"章节「{row.title}」窗口仅 {window} 秒（< {SHORT_CHAPTER_SECONDS}s），"
                        f"与上一章间距过近"
                    ),
                    suggestion="折叠进前一章（标题用 / 合并），避免切片出现空镜头",
                    severity="info",
                    window_start=folded_rows[-1].start_seconds,
                    window_end=row.start_seconds,
                )
            )
            continue
        folded_rows.append(row)

    # ---- 6) 相邻缺口 > 8 分钟（只判相邻章节之间的空档，片尾 outro 不算缺口） ----
    for position, row in enumerate(folded_rows):
        if position + 1 >= len(folded_rows):
            break
        gap_end = folded_rows[position + 1].start_seconds
        gap = gap_end - row.start_seconds
        if gap > GAP_WARNING_SECONDS:
            suggestion_start = row.start_seconds + 60
            suggestion_end = gap_end - 60
            gap_issue = IssueDraft(
                kind=IssueKind.GAP_WARNING.value,
                issue_key=f"{episode_code}:gap:{row.start_seconds}-{gap_end}",
                chapter_id=row.chapter_id,
                message=(
                    f"「{row.title}」到下一章之间空了 {gap // 60} 分 {gap % 60} 秒"
                    f"（> {GAP_WARNING_SECONDS // 60} 分钟）"
                ),
                suggestion=(
                    f"建议补一章 {to_short_timecode(suggestion_start)}–{to_short_timecode(suggestion_end)} "
                    f"（约 {(gap - 120) // 60} 分钟）或确认该段无内容"
                ),
                severity="warn",
                window_start=row.start_seconds,
                window_end=gap_end,
            )
            result.issues.append(gap_issue)
            result.gaps.append(
                {
                    "issue_key": gap_issue.issue_key,
                    "from_start": row.start_seconds,
                    "to_start": gap_end,
                    "gap_seconds": gap,
                    "suggestion_start": suggestion_start,
                    "suggestion_end": suggestion_end,
                }
            )

    result.corrected = folded_rows
    return result


def chapter_inputs(chapters) -> list[ChapterInput]:
    """ORM Chapter -> 纯函数输入（保持行序）。"""
    rows = sorted(chapters, key=lambda item: item.ordinal)
    return [
        ChapterInput(
            id=item.id,
            ordinal=item.ordinal,
            start_seconds=item.start_seconds,
            title=item.title,
            confidence=item.confidence or 0.0,
            source=item.source or ChapterSource.PARSE.value,
            raw_text=item.raw_text or "",
        )
        for item in rows
    ]

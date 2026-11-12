"""算法 2「章节窗口不变量校验」纯函数单测。

覆盖五条不变量：严格递增 / 末章 ≤ 时长 / 重叠合并 / <20s 折叠 / 缺口 >8min。
所有输入都是普通 dataclass，不连 DB、不碰 ORM。
"""
from __future__ import annotations

import pytest

from src.constants.limits import (
    GAP_WARNING_SECONDS,
    OVERLAP_TOLERANCE_SECONDS,
    SHORT_CHAPTER_SECONDS,
)
from src.services.validation_service import ChapterInput, validate_episode


def chapter(
    ordinal: int,
    start: int | None,
    title: str | None = None,
    confidence: float = 0.9,
    cid: int | None = None,
    source: str = "parse",
    raw_text: str = "",
) -> ChapterInput:
    return ChapterInput(
        id=cid if cid is not None else ordinal + 1,
        ordinal=ordinal,
        start_seconds=start,
        title=title if title is not None else f"章节{ordinal + 1}",
        confidence=confidence,
        source=source,
        raw_text=raw_text,
    )


# ---------------------------------------------------------------- 正常路径


def test_clean_increasing_timeline_has_no_issue():
    rows = [chapter(0, 60), chapter(1, 300), chapter(2, 600)]
    result = validate_episode("EP-T01", 900, rows)
    assert result.issue_count == 0
    assert result.reordered == 0
    assert result.merged == 0
    assert result.folded == 0
    assert result.gaps == []
    assert [row.start_seconds for row in result.corrected] == [60, 300, 600]
    assert result.kind_counts() == {}


def test_single_chapter_has_no_issue():
    result = validate_episode("EP-T02", 900, [chapter(0, 120)])
    assert result.issue_count == 0
    assert len(result.corrected) == 1
    assert result.corrected[0].start_seconds == 120
    assert result.corrected[0].auto_fixed is False


def test_out_of_order_is_reported_and_corrected():
    rows = [chapter(0, 60), chapter(1, 300), chapter(2, 120), chapter(3, 500)]
    result = validate_episode("EP-T03", 900, rows)
    assert result.reordered == 1
    assert result.issue_count == 1
    assert result.kind_counts() == {"out_of_order": 1}
    issue = result.issues[0]
    assert issue.issue_key == "EP-T03:out_of_order:3"
    assert issue.chapter_id == 3
    assert issue.window_start == 120
    assert issue.severity == "warn"
    assert "02:00" in issue.message and "05:00" in issue.message
    assert [row.start_seconds for row in result.corrected] == [60, 120, 300, 500]


def test_reordered_and_overlap_combined_counts():
    # 行序：60, 300, 120, 240(.9), 240(.8), 500 → 3 条乱序 + 1 组重叠
    rows = [
        chapter(0, 60, "A"),
        chapter(1, 300, "B"),
        chapter(2, 120, "C"),
        chapter(3, 240, "D", confidence=0.9, cid=4),
        chapter(4, 240, "E", confidence=0.8, cid=5),
        chapter(5, 500, "F"),
    ]
    result = validate_episode("EP-T04", 900, rows)
    assert result.reordered == 3
    assert result.merged == 1
    assert result.folded == 0
    assert result.kind_counts() == {"out_of_order": 3, "overlap": 1}
    assert [row.start_seconds for row in result.corrected] == [60, 120, 240, 300, 500]
    merged_row = result.corrected[2]
    assert merged_row.title == "D / E"
    assert merged_row.confidence == pytest.approx(0.9, abs=1e-9)
    assert merged_row.auto_fixed is True
    assert merged_row.merged_from == [4, 5]


def test_overlap_keeps_higher_confidence_and_merges_titles():
    rows = [
        chapter(0, 300, "低置信", confidence=0.7, cid=11),
        chapter(1, 300, "高置信", confidence=0.95, cid=12),
    ]
    result = validate_episode("EP-T05", 900, rows)
    assert result.merged == 1
    assert len(result.corrected) == 1
    row = result.corrected[0]
    assert row.chapter_id == 12  # 置信高者保留
    assert row.title == "低置信 / 高置信"  # 标题按行序合并且不重复
    assert row.confidence == pytest.approx(0.95, abs=1e-9)
    assert row.merged_from == [11, 12]


def test_over_duration_is_block_issue_and_kept_in_corrected():
    rows = [chapter(0, 800), chapter(1, 1000)]
    result = validate_episode("EP-T06", 900, rows)
    assert result.kind_counts() == {"over_duration": 1}
    issue = result.issues[0]
    assert issue.severity == "block"
    assert issue.window_start == 1000
    assert issue.window_end == 900
    assert "16:40" in issue.message and "15:00" in issue.message
    assert [row.start_seconds for row in result.corrected] == [800, 1000]


def test_chapter_equal_to_duration_is_allowed():
    result = validate_episode("EP-T07", 900, [chapter(0, 800), chapter(1, 900)])
    assert result.kind_counts() == {}
    assert [row.start_seconds for row in result.corrected] == [800, 900]


def test_too_short_chapter_folds_into_previous():
    result = validate_episode("EP-T08", 300, [chapter(0, 0, "A"), chapter(1, 10, "B")])
    assert result.folded == 1
    assert len(result.corrected) == 1
    row = result.corrected[0]
    assert row.start_seconds == 0
    assert row.title == "A / B"
    assert row.auto_fixed is True
    assert "过短折叠" in row.fix_note
    issue = result.issues[0]
    assert issue.kind == "too_short"
    assert issue.severity == "info"
    assert issue.window_start == 0
    assert issue.window_end == 10
    assert "10 秒" in issue.message


def test_exactly_short_threshold_is_not_folded():
    # < 20s 才折叠；正好 20s 保持两章
    result = validate_episode("EP-T09", 300, [chapter(0, 0), chapter(1, SHORT_CHAPTER_SECONDS)])
    assert result.folded == 0
    assert len(result.corrected) == 2
    assert result.kind_counts() == {}


def test_gap_over_threshold_emits_warning_and_suggestion():
    result = validate_episode("EP-T10", 1200, [chapter(0, 0), chapter(1, 600)])
    assert result.kind_counts() == {"gap_warning": 1}
    issue = result.issues[0]
    assert issue.severity == "warn"
    assert issue.window_start == 0 and issue.window_end == 600
    assert "10 分 0 秒" in issue.message
    assert "01:00–09:00" in issue.suggestion
    assert "8 分钟" in issue.suggestion
    assert result.gaps == [
        {
            "issue_key": "EP-T10:gap:0-600",
            "from_start": 0,
            "to_start": 600,
            "gap_seconds": 600,
            "suggestion_start": 60,
            "suggestion_end": 540,
        }
    ]


def test_gap_equal_to_threshold_is_not_reported():
    result = validate_episode(
        "EP-T11", 1200, [chapter(0, 0), chapter(1, GAP_WARNING_SECONDS)]
    )
    assert result.kind_counts() == {}
    assert result.gaps == []


# ---------------------------------------------------------------- 边界 / 降级


def test_empty_chapter_list_reports_single_block_issue():
    result = validate_episode("EP-T12", 900, [])
    assert result.corrected == []
    assert result.unparsed == 0
    assert result.issue_count == 1
    issue = result.issues[0]
    assert issue.kind == "unparsed"
    assert issue.issue_key == "EP-T12:unparsed:all"
    assert issue.chapter_id is None
    assert issue.severity == "block"


def test_all_unparsed_reports_row_issues_plus_all_issue():
    rows = [
        chapter(0, None, "1h02m 未识别 A", source="unparsed", raw_text="1h02m 未识别 A"),
        chapter(1, None, "2h03m 未识别 B", source="unparsed", raw_text="2h03m 未识别 B"),
    ]
    result = validate_episode("EP-T13", 900, rows)
    assert result.unparsed == 2
    assert result.corrected == []
    assert result.issue_count == 3
    assert result.kind_counts() == {"unparsed": 3}
    keys = {issue.issue_key for issue in result.issues}
    assert keys == {"EP-T13:unparsed:1", "EP-T13:unparsed:2", "EP-T13:unparsed:all"}


def test_mixed_unparsed_and_parsed_rows():
    rows = [
        chapter(0, 60, "有效"),
        chapter(1, None, "坏行", source="unparsed", raw_text="坏行"),
        chapter(2, 300, "有效2"),
    ]
    result = validate_episode("EP-T14", 900, rows)
    assert result.unparsed == 1
    assert result.issue_count == 1
    assert result.issues[0].kind == "unparsed"
    assert result.issues[0].window_start is None
    assert [row.start_seconds for row in result.corrected] == [60, 300]


def test_negative_start_is_not_silently_clamped():
    # 纯函数不做入参范围校验（写入层 _assert_range 负责 422），但绝不能静默改成正数：
    # -5 < 初始 running_max(-1)，按行序记一条 out_of_order 显式降级。
    result = validate_episode("EP-T15", 900, [chapter(0, -5)])
    assert result.corrected[0].start_seconds == -5
    assert result.kind_counts() == {"out_of_order": 1}
    assert OVERLAP_TOLERANCE_SECONDS == 0  # 重叠判定按同一时间点（容差 0）


# ---------------------------------------------------------------- 性质 / 不变量


@pytest.mark.parametrize(
    ("duration", "rows"),
    [
        (900, [chapter(0, 60), chapter(1, 300), chapter(2, 600)]),
        (300, [chapter(0, 0), chapter(1, 10)]),
        (1200, [chapter(0, 0), chapter(1, 600)]),
        (900, [chapter(0, 60), chapter(1, 300), chapter(2, 120), chapter(3, 500)]),
        (3600, [chapter(0, 2400), chapter(1, 350), chapter(2, 720), chapter(3, 720)]),
    ],
)
def test_corrected_starts_are_strictly_increasing(duration, rows):
    result = validate_episode("EP-P01", duration, rows)
    starts = [row.start_seconds for row in result.corrected]
    assert all(starts[index] > starts[index - 1] for index in range(1, len(starts)))
    assert len(starts) == len([row for row in rows if row.start_seconds is not None]) - result.merged - result.folded


def test_validation_is_deterministic():
    rows = [
        chapter(0, 2400, "末尾"),
        chapter(1, 350, "A"),
        chapter(2, 720, "B", cid=3),
        chapter(3, 720, "C", confidence=0.95, cid=4),
    ]
    first = validate_episode("EP-P02", 3600, rows)
    second = validate_episode("EP-P02", 3600, rows)
    assert first.to_plan() == second.to_plan()
    assert [(row.start_seconds, row.title) for row in first.corrected] == [
        (row.start_seconds, row.title) for row in second.corrected
    ]


def test_result_ignores_input_order_for_corrected_start_set():
    # 行序会决定「乱序」判定，但修正后的时间点集合与顺序必须一致
    forward = validate_episode(
        "EP-P03", 900, [chapter(0, 60), chapter(1, 300), chapter(2, 120)]
    )
    shuffled = validate_episode(
        "EP-P03", 900, [chapter(0, 120), chapter(1, 60), chapter(2, 300)]
    )
    assert [row.start_seconds for row in forward.corrected] == [60, 120, 300]
    assert [row.start_seconds for row in shuffled.corrected] == [60, 120, 300]
    assert forward.kind_counts() == {"out_of_order": 1}
    assert shuffled.kind_counts() == {"out_of_order": 1}


def test_issue_count_equals_sum_of_kind_counts():
    rows = [
        chapter(0, 2400),
        chapter(1, 350),
        chapter(2, 720),
        chapter(3, 720),
        chapter(4, None, source="unparsed"),
    ]
    result = validate_episode("EP-P04", 3600, rows)
    assert result.issue_count == sum(result.kind_counts().values())
    assert result.to_plan()["issue_count"] == result.issue_count
    assert result.to_plan()["kind_counts"] == result.kind_counts()
    assert result.to_plan()["reordered"] == result.reordered
    assert result.to_plan()["merged"] == result.merged
    assert result.to_plan()["folded"] == result.folded

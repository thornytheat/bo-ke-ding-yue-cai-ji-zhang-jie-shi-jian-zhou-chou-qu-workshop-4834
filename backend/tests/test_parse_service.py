"""算法 1「时间戳解析与归一」纯函数单测。

输入取自 seed 里真实出现过的 show notes 写法（见 batch-plan §5.3 与
backend/scripts/demo_config.py），期望值为手算秒数 + 常量表里的置信度。
"""
from __future__ import annotations

import pytest

from src.constants.limits import (
    CONFIDENCE_ABOUT_MINUTES,
    CONFIDENCE_AT,
    CONFIDENCE_CN_CLOCK,
    CONFIDENCE_HHMMSS,
    CONFIDENCE_MMSS,
    CONFIDENCE_NO_TITLE_PENALTY,
    MAX_SHOW_NOTES_CHARS,
    MAX_TITLE_CHARS,
)
from src.services.parse_service import parse_show_notes, parse_timestamp

DUR_SHORT = 31 * 60 + 20  # 31:20
DUR_LONG = 69 * 60  # 4140s（EP-035 口径，1:11 有歧义）


def test_hh_mm_ss_normal_path():
    entry = parse_timestamp("01:23:45 主题", DUR_LONG)
    assert entry is not None
    assert entry.seconds == 5025  # 1*3600 + 23*60 + 45
    assert entry.rule == "hh_mm_ss"
    assert entry.title == "主题"
    assert entry.confidence == pytest.approx(CONFIDENCE_HHMMSS, abs=1e-6)
    assert entry.ambiguous is False


def test_mm_ss_normal_path():
    entry = parse_timestamp("12:30 混响的空间感", DUR_SHORT)
    assert entry.seconds == 750  # 12*60 + 30
    assert entry.rule == "mm_ss"
    assert entry.title == "混响的空间感"
    assert entry.confidence == pytest.approx(CONFIDENCE_MMSS, abs=1e-6)


def test_cn_hour_minute_second_normal_path():
    entry = parse_timestamp("1时02分30秒 三小时里被剪掉的段落", DUR_LONG)
    assert entry.seconds == 3750  # 3600 + 120 + 30
    assert entry.rule == "cn_hour"
    assert entry.title == "三小时里被剪掉的段落"
    assert entry.confidence == pytest.approx(CONFIDENCE_CN_CLOCK, abs=1e-6)


def test_cn_minute_second_normal_path():
    entry = parse_timestamp("45分30秒 返程路上的复盘", DUR_LONG)
    assert entry.seconds == 2730  # 45*60 + 30
    assert entry.rule == "cn_minute"
    assert entry.title == "返程路上的复盘"


def test_about_minutes_normal_path():
    entry = parse_timestamp("约 12 分钟处 骑楼下的茶摊与老醋", DUR_LONG)
    assert entry.seconds == 720  # 12*60
    assert entry.rule == "about_minutes"
    assert entry.confidence == pytest.approx(CONFIDENCE_ABOUT_MINUTES, abs=1e-6)
    assert entry.title == "骑楼下的茶摊与老醋"


def test_at_mmss_normal_path():
    entry = parse_timestamp("@12:30 混响", DUR_SHORT)
    assert entry.seconds == 750
    assert entry.rule == "at_mmss"
    assert entry.confidence == pytest.approx(CONFIDENCE_AT, abs=1e-6)


def test_cn_hour_zero_hour_path():
    entry = parse_timestamp("0时08分10秒 三小时里被剪掉的段落", DUR_LONG)
    assert entry.seconds == 490  # 0*3600 + 8*60 + 10
    assert entry.rule == "cn_hour"


def test_mm_ss_marks_ambiguous_on_long_episode():
    # 69 分钟的单集里 "1:11" 也可读成 1 时 11 分，必须标歧义（seed 的 EP-035 口径）
    entry = parse_timestamp("1:11 开场闲聊", DUR_LONG)
    assert entry.seconds == 71
    assert entry.ambiguous is True
    assert entry.rule == "mm_ss"


def test_mm_ss_not_ambiguous_on_short_episode():
    entry = parse_timestamp("1:11 开场闲聊", DUR_SHORT)
    assert entry.seconds == 71
    assert entry.ambiguous is False


def test_explicit_hh_mm_ss_never_ambiguous():
    # 用户明确写了三段，即使单集 ≥60 分钟也不能标歧义
    entry = parse_timestamp("1:02:03 主题", DUR_LONG)
    assert entry.seconds == 3723
    assert entry.rule == "hh_mm_ss"
    assert entry.ambiguous is False


def test_missing_title_gets_penalty_and_placeholder():
    entry = parse_timestamp("12:30", DUR_SHORT)
    assert entry.title == "未命名章节"
    assert entry.confidence == pytest.approx(
        round(CONFIDENCE_MMSS - CONFIDENCE_NO_TITLE_PENALTY, 3), abs=1e-6
    )


def test_unrecognized_timestamp_is_preserved_as_unparsed():
    raw = "1h02m 听众问答（时间码格式未识别）"
    entry = parse_timestamp(raw, DUR_LONG)
    assert entry is not None
    assert entry.seconds is None
    assert entry.rule == "unrecognized"
    assert entry.confidence == pytest.approx(0.0, abs=1e-9)
    assert entry.source == "unparsed"
    assert entry.raw == raw  # 原文必须保留给异常队列


def test_plain_prose_line_is_ignored():
    assert parse_timestamp("本期我们聊了三个话题", DUR_LONG) is None


def test_seconds_over_59_degrades_to_unparsed():
    # 12:75 不是合法 mm:ss；不能静默截成 750 秒，只能降级为未识别并保留原文
    entry = parse_timestamp("12:75 坏秒", DUR_LONG)
    assert entry is not None
    assert entry.seconds is None
    assert entry.rule == "unrecognized"


def test_minutes_over_59_in_clock_degrades_to_unparsed():
    entry = parse_timestamp("01:99:00 坏分", DUR_LONG)
    assert entry is not None
    assert entry.seconds is None
    assert entry.rule == "unrecognized"


def test_list_bullet_and_separators_stripped_from_title():
    entry = parse_timestamp("• @03:12 —— 片尾曲", DUR_SHORT)
    assert entry.seconds == 192
    assert entry.title == "片尾曲"


def test_title_is_truncated_to_max_chars():
    entry = parse_timestamp("12:30 " + "字" * (MAX_TITLE_CHARS + 20), DUR_SHORT)
    assert len(entry.title) == MAX_TITLE_CHARS


def test_parse_show_notes_aggregate_counts():
    text = "\n".join(
        [
            "这期聊三个话题",
            "00:00 开场",
            "01:30 第一个话题",
            "• 8分10秒 第二个话题",
            "约 12 分钟处 茶摊",
            "1h02m 听众问答",
            "",
            "结尾闲聊",
        ]
    )
    result = parse_show_notes(text, DUR_LONG)
    assert result.total_rows == 5
    assert [entry.seconds for entry in result.entries] == [0, 90, 490, 720, None]
    assert result.ignored_lines == 3
    assert len(result.unparsed) == 1
    assert result.unparsed[0].rule == "unrecognized"
    # 69 分钟的单集里 mm:ss 全部可能被读成 h:mm，按现有口径标歧义（含 00:00 / 01:30）
    assert result.ambiguous_count == 2
    assert result.entries[0].ambiguous is True
    assert result.entries[1].ambiguous is True
    assert result.entries[2].ambiguous is False  # cn_minute 不走歧义分支
    assert result.rule_usage == {
        "mm_ss": 2,
        "cn_minute": 1,
        "about_minutes": 1,
        "unrecognized": 1,
    }
    assert len(result.chapters) == 4


def test_parse_show_notes_clips_at_max_chars():
    text = "00:00 开场\n" + "x" * MAX_SHOW_NOTES_CHARS + "\n12:30 超出截断范围"
    result = parse_show_notes(text, DUR_LONG)
    assert result.total_rows == 1
    assert result.entries[0].title == "开场"
    assert all("截断" not in entry.title for entry in result.entries)


def test_parse_timestamp_is_alias_of_parse_line():
    for raw in ("12:30 混响", "约 12 分钟处 茶摊", "1h02m 未识别"):
        entry = parse_timestamp(raw, DUR_LONG)
        assert entry.raw == raw
        assert entry.source in {"parse", "unparsed"}

"""时间码 / 时长归一工具单测（录音棚口径：H:MM:SS 与 MM:SS）。"""
from __future__ import annotations

import pytest

from src.utils.timecode import (
    human_duration,
    to_gap_text,
    to_short_timecode,
    to_timecode,
)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "00:00:00"),
        (59, "00:00:59"),
        (720, "00:12:00"),
        (5025, "01:23:45"),
        (36000, "10:00:00"),
    ],
)
def test_to_timecode_exact_values(seconds, expected):
    assert to_timecode(seconds) == expected


def test_to_timecode_none_placeholder():
    assert to_timecode(None) == "--:--:--"


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "00:00"),
        (59, "00:59"),
        (720, "12:00"),
        (3599, "59:59"),
        (3750, "1:02:30"),
        (4140, "1:09:00"),
    ],
)
def test_to_short_timecode_exact_values(seconds, expected):
    assert to_short_timecode(seconds) == expected


def test_to_short_timecode_none_placeholder():
    assert to_short_timecode(None) == "--:--"


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "0m00s"),
        (59, "0m59s"),
        (720, "12m00s"),
        (3661, "1h01m"),
        (3750, "1h02m"),
    ],
)
def test_human_duration_exact_values(seconds, expected):
    assert human_duration(seconds) == expected


def test_human_duration_none_placeholder():
    assert human_duration(None) == "—"


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "0 分"),
        (60, "1 分"),
        (600, "10 分"),
        (620, "10 分 20 秒"),
        (3599, "59 分 59 秒"),
    ],
)
def test_to_gap_text_exact_values(seconds, expected):
    assert to_gap_text(seconds) == expected


def test_negative_values_are_clamped_to_zero_not_wrapped():
    # 负值明确降级为 00:00:00，不允许出现 "-1:00" 这类脏时间码
    assert to_timecode(-1) == "00:00:00"
    assert to_short_timecode(-61) == "00:00"
    assert human_duration(-10) == "0m00s"


def test_timecode_round_trip_parses_back_to_same_seconds():
    from src.services.parse_service import parse_timestamp

    for seconds in (0, 71, 720, 3750, 5025):
        entry = parse_timestamp(to_timecode(seconds), 7200)
        assert entry is not None
        assert entry.seconds == seconds

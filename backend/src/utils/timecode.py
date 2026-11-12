"""时间码格式化：录音棚口径 H:MM:SS / MM:SS。"""
from __future__ import annotations


def to_timecode(seconds: int | None) -> str:
    """720 -> 00:12:00（railed，录音棚走带时间码）。"""
    if seconds is None:
        return "--:--:--"
    value = max(0, int(seconds))
    hours, rest = divmod(value, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def to_short_timecode(seconds: int | None) -> str:
    """720 -> 12:00；超过 1 小时 -> 1:02:30。"""
    if seconds is None:
        return "--:--"
    value = max(0, int(seconds))
    hours, rest = divmod(value, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def human_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    value = max(0, int(seconds))
    hours, rest = divmod(value, 3600)
    minutes = rest // 60
    if hours:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m{rest % 60:02d}s"


def to_gap_text(seconds: int) -> str:
    minutes = seconds // 60
    rest = seconds % 60
    return f"{minutes} 分 {rest} 秒" if rest else f"{minutes} 分"

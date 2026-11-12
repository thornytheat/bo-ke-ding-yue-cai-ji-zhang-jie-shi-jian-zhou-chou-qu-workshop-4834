"""时间戳解析与归一（算法 1，纯函数、无 DB、无随机）。

支持的写法族：
  hh:mm:ss        01:23:45 / 1:02:03
  mm:ss           12:30 / 03:12           （60 分钟以上的单集里可能被读成 h:mm → ambiguous）
  X时Y分Z秒        1时02分30秒 / 2时15分 / 45分30秒
  X分Y秒           45分30秒 / 12分
  约 N 分钟处       约 12 分钟处 / 约12分钟 / 约 8 分处
  @mm:ss          @12:30
规则按优先级匹配，命中即返回；都命中不了但"看起来像时间码"的行标记 unparsed 并保留原文。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.constants.enums import ChapterSource
from src.constants.limits import (
    AMBIGUOUS_MIN_DURATION_SECONDS,
    CONFIDENCE_ABOUT_MINUTES,
    CONFIDENCE_AT,
    CONFIDENCE_CN_CLOCK,
    CONFIDENCE_HHMMSS,
    CONFIDENCE_MMSS,
    CONFIDENCE_NO_TITLE_PENALTY,
    MAX_SHOW_NOTES_CHARS,
    MAX_TITLE_CHARS,
)

# 行首允许的前缀：列表符号 / 项目符号 / 空白
_LEAD = r"^[\s\-–—•·*>\t|]*"

_TITLE_SEPARATORS = re.compile(r"^[\s\-–—:：·|｜/、,，.。]+")

# 「看起来像时间码」的行首判定：只有行首就是数字+时间单位/冒号的行才会保留为 unparsed，
# 正文里提到"时长 44 分钟"这类句子不会被误判成章节
_TIMEISH = re.compile(
    _LEAD + r"(?:约\s*)?(\d{1,3}\s*(?:小时|时|分钟|分|秒|[:：])|@\s*\d|\d{1,3}\s*[hm]\d*)",
    re.I,
)

_RULES: list[tuple[str, re.Pattern[str], float]] = [
    # @mm:ss —— 平台页最常见的锚点写法
    ("at_mmss", re.compile(_LEAD + r"@\s*(\d{1,3})\s*[:：]\s*(\d{2})(?!\d)"), CONFIDENCE_AT),
    # hh:mm:ss
    ("hh_mm_ss", re.compile(_LEAD + r"(\d{1,2})\s*[:：]\s*(\d{2})\s*[:：]\s*(\d{2})(?!\d)"), CONFIDENCE_HHMMSS),
    # 约 N 分钟处 / 约 N 分处
    ("about_minutes", re.compile(_LEAD + r"约\s*(\d{1,3})\s*(?:分钟?|分)\s*(?:处|左右|的位置|时)?"), CONFIDENCE_ABOUT_MINUTES),
    # X时Y分Z秒 / X时Y分 / X时
    (
        "cn_hour",
        re.compile(_LEAD + r"(\d{1,2})\s*时\s*(?:(\d{1,2})\s*分)?\s*(?:(\d{1,2})\s*秒)?"),
        CONFIDENCE_CN_CLOCK,
    ),
    # X分Y秒 / X分
    ("cn_minute", re.compile(_LEAD + r"(\d{1,3})\s*分\s*(?:(\d{1,2})\s*秒)?"), CONFIDENCE_CN_CLOCK),
    # mm:ss —— 放最后，避免抢走 hh:mm:ss
    ("mm_ss", re.compile(_LEAD + r"(\d{1,3})\s*[:：]\s*(\d{2})(?!\d)"), CONFIDENCE_MMSS),
]


@dataclass
class ParsedEntry:
    raw: str
    title: str
    seconds: int | None
    rule: str
    confidence: float
    ambiguous: bool = False
    source: str = ChapterSource.PARSE.value


@dataclass
class ParseResult:
    entries: list[ParsedEntry] = field(default_factory=list)
    unparsed: list[ParsedEntry] = field(default_factory=list)
    ignored_lines: int = 0
    ambiguous_count: int = 0
    rule_usage: dict[str, int] = field(default_factory=dict)

    @property
    def chapters(self) -> list[ParsedEntry]:
        return [entry for entry in self.entries if entry.seconds is not None]

    @property
    def total_rows(self) -> int:
        return len(self.entries)


def _extract_title(rest: str) -> str:
    title = _TITLE_SEPARATORS.sub("", rest or "").strip()
    if not title:
        return "未命名章节"
    return title[:MAX_TITLE_CHARS]


def _seconds_from_cn(hours: str | None, minutes: str | None, secs: str | None) -> int:
    total = 0
    if hours:
        total += int(hours) * 3600
    if minutes:
        total += int(minutes) * 60
    if secs:
        total += int(secs)
    return total


def parse_line(line: str, duration_seconds: int) -> ParsedEntry | None:
    """解析单行；返回 None 表示这行既不是时间码、也不是可保留的未识别时间码。"""
    text = line.strip()
    if not text:
        return None

    for rule, pattern, confidence in _RULES:
        match = pattern.match(text)
        if not match:
            continue

        groups = match.groups()
        rest = text[match.end():]
        title = _extract_title(rest)
        ambiguous = False
        seconds = 0

        if rule == "hh_mm_ss":
            hours, minutes, secs = int(groups[0]), int(groups[1]), int(groups[2])
            if minutes > 59 or secs > 59:
                continue
            seconds = hours * 3600 + minutes * 60 + secs
        elif rule == "mm_ss":
            minutes, secs = int(groups[0]), int(groups[1])
            if secs > 59:
                continue
            seconds = minutes * 60 + secs
            # 60 分钟以上的单集里，"1:23" 既可能是 1 分 23 秒，也可能是 1 时 23 分
            if (
                minutes < 60
                and duration_seconds >= AMBIGUOUS_MIN_DURATION_SECONDS
                and minutes * 3600 + secs <= duration_seconds
            ):
                ambiguous = True
        elif rule == "at_mmss":
            minutes, secs = int(groups[0]), int(groups[1])
            if secs > 59:
                continue
            seconds = minutes * 60 + secs
            if (
                minutes < 60
                and duration_seconds >= AMBIGUOUS_MIN_DURATION_SECONDS
                and minutes * 3600 + secs <= duration_seconds
            ):
                ambiguous = True
        elif rule == "about_minutes":
            seconds = int(groups[0]) * 60
        elif rule == "cn_hour":
            if groups[1] and int(groups[1]) > 59:
                continue
            if groups[2] and int(groups[2]) > 59:
                continue
            seconds = _seconds_from_cn(groups[0], groups[1], groups[2])
        elif rule == "cn_minute":
            if groups[1] and int(groups[1]) > 59:
                continue
            seconds = _seconds_from_cn(None, groups[0], groups[1])
        else:  # pragma: no cover - 规则表固定
            continue

        if title == "未命名章节":
            confidence = max(0.2, confidence - CONFIDENCE_NO_TITLE_PENALTY)
        return ParsedEntry(
            raw=text,
            title=title,
            seconds=seconds,
            rule=rule,
            confidence=round(confidence, 3),
            ambiguous=ambiguous,
        )

    # 没命中任何规则：只有行首就是时间码形态的行才保留为 unparsed，其余当正文忽略
    if _TIMEISH.match(text):
        return ParsedEntry(
            raw=text,
            title=_extract_title(text),
            seconds=None,
            rule="unrecognized",
            confidence=0.0,
            source=ChapterSource.UNPARSED.value,
        )
    return None


def parse_show_notes(text: str, duration_seconds: int) -> ParseResult:
    """逐行解析 show notes；同时间点不在这里去重（交给不变量校验）。"""
    result = ParseResult()
    clipped = (text or "")[:MAX_SHOW_NOTES_CHARS]
    for line in clipped.splitlines():
        entry = parse_line(line, duration_seconds)
        if entry is None:
            result.ignored_lines += 1
            continue
        result.entries.append(entry)
        result.rule_usage[entry.rule] = result.rule_usage.get(entry.rule, 0) + 1
        if entry.seconds is None:
            result.unparsed.append(entry)
        if entry.ambiguous:
            result.ambiguous_count += 1
    return result


def parse_timestamp(raw: str, duration_seconds: int) -> ParsedEntry | None:
    """人工补录时复用同一套规则（前端不做任何解析）。"""
    return parse_line(raw, duration_seconds)

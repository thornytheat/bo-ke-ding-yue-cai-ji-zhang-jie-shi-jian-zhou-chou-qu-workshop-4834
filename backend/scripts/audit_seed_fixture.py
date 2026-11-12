"""开发期自检：不连数据库，直接跑 seed 用的解析 + 不变量校验，核对契约数字。

用法：cd backend && python3 scripts/audit_seed_fixture.py

断言：feeds=6 episodes=48 chapters=260 issues=22（乱序 12 / 重叠 3 / 缺口 3 / 未识别 4）
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scripts.demo_config import EPISODES, FEEDS  # noqa: E402
from src.constants.enums import IssueKind  # noqa: E402
from src.services.parse_service import parse_show_notes  # noqa: E402
from src.services.validation_service import ChapterInput, validate_episode  # noqa: E402

EXPECTED = {
    "feeds": 6,
    "episodes": 48,
    "chapters": 260,
    "issues": 22,
    "unparsed": 4,
    "out_of_order": 12,
    "overlap": 3,
    "gap_warning": 3,
}


def main() -> int:
    chapters_total = 0
    issues_total = 0
    kind_total: Counter[str] = Counter()
    rows: list[str] = []

    for episode in EPISODES:
        parsed = parse_show_notes(episode.show_notes, episode.duration_seconds)
        chapters_total += len(parsed.entries)
        inputs = [
            ChapterInput(
                id=None,
                ordinal=index,
                start_seconds=entry.seconds,
                title=entry.title,
                confidence=entry.confidence,
                source=entry.source,
                raw_text=entry.raw,
            )
            for index, entry in enumerate(parsed.entries)
        ]
        result = validate_episode(episode.code, episode.duration_seconds, inputs)
        issues_total += result.issue_count
        kind_total.update(result.kind_counts())
        if result.issue_count:
            rows.append(
                f"{episode.code} {episode.title[:18]:<20} "
                f"ch={len(parsed.entries):>2} issues={result.issue_count} {dict(result.kind_counts())}"
            )

    print("== 有异常的单集 ==")
    for row in rows:
        print(row)
    print()
    print("== 合计 ==")
    print(f"feeds={len(FEEDS)} episodes={len(EPISODES)} chapters={chapters_total} issues={issues_total}")
    print(f"kinds={dict(sorted(kind_total.items()))}")

    actual = {
        "feeds": len(FEEDS),
        "episodes": len(EPISODES),
        "chapters": chapters_total,
        "issues": issues_total,
        "unparsed": kind_total.get(IssueKind.UNPARSED.value, 0),
        "out_of_order": kind_total.get(IssueKind.OUT_OF_ORDER.value, 0),
        "overlap": kind_total.get(IssueKind.OVERLAP.value, 0),
        "gap_warning": kind_total.get(IssueKind.GAP_WARNING.value, 0),
    }
    drift = {key: (EXPECTED[key], actual[key]) for key in EXPECTED if EXPECTED[key] != actual[key]}
    if drift:
        print()
        print("!! 与契约不一致 (expected, actual):")
        for key, pair in drift.items():
            print(f"   {key}: {pair[0]} != {pair[1]}")
        return 1
    print()
    print("OK seed fixture matches contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""共享枚举（后端唯一定义处）。前端副本见 frontend/src/constants/enums.ts。

README「共享枚举出现位置」一节列出全部出现点，改动需两侧同步。
"""
from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """三角色：运营主管 / 内容运营 / 剪辑师（只读）。"""

    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class FeedKind(StrEnum):
    """订阅源类型：RSS XML / 平台 JSON / 目录 HTML。"""

    RSS = "rss"
    PLATFORM = "platform"
    APPLE = "apple"


class IngestState(StrEnum):
    """单集采集状态：水位线之后新到达待入库 / 已同步。"""

    PENDING = "pending"
    SYNCED = "synced"


class ParseStatus(StrEnum):
    """单集章节解析状态。"""

    PENDING = "pending"
    PARSED = "parsed"
    PARTIAL = "partial"
    FAILED = "failed"


class ChapterSource(StrEnum):
    """章节来源：自动解析 / 人工补录 / 解析失败保留原文。"""

    PARSE = "parse"
    MANUAL = "manual"
    UNPARSED = "unparsed"


class IssueKind(StrEnum):
    """章节窗口不变量违反类型（异常队列按此分组）。"""

    OUT_OF_ORDER = "out_of_order"
    OVERLAP = "overlap"
    OVER_DURATION = "over_duration"
    TOO_SHORT = "too_short"
    GAP_WARNING = "gap_warning"
    UNPARSED = "unparsed"


class IssueStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class TaskMode(StrEnum):
    INGEST = "ingest"
    PARSE = "parse"
    BOTH = "both"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


FEED_KIND_LABELS: dict[str, str] = {
    FeedKind.RSS.value: "RSS 订阅",
    FeedKind.PLATFORM.value: "平台接口",
    FeedKind.APPLE.value: "目录 HTML",
}

INGEST_STATE_LABELS: dict[str, str] = {
    IngestState.PENDING.value: "待入库",
    IngestState.SYNCED.value: "已同步",
}

PARSE_STATUS_LABELS: dict[str, str] = {
    ParseStatus.PENDING.value: "待解析",
    ParseStatus.PARSED.value: "已解析",
    ParseStatus.PARTIAL.value: "部分解析",
    ParseStatus.FAILED.value: "解析失败",
}

CHAPTER_SOURCE_LABELS: dict[str, str] = {
    ChapterSource.PARSE.value: "自动解析",
    ChapterSource.MANUAL.value: "人工补录",
    ChapterSource.UNPARSED.value: "未识别",
}

ISSUE_KIND_LABELS: dict[str, str] = {
    IssueKind.OUT_OF_ORDER.value: "乱序",
    IssueKind.OVERLAP.value: "重叠",
    IssueKind.OVER_DURATION.value: "超时长",
    IssueKind.TOO_SHORT.value: "过短折叠",
    IssueKind.GAP_WARNING.value: "缺口告警",
    IssueKind.UNPARSED.value: "未识别",
}

ISSUE_KIND_ORDER: list[str] = [
    IssueKind.OUT_OF_ORDER.value,
    IssueKind.OVERLAP.value,
    IssueKind.OVER_DURATION.value,
    IssueKind.TOO_SHORT.value,
    IssueKind.GAP_WARNING.value,
    IssueKind.UNPARSED.value,
]

ISSUE_STATUS_LABELS: dict[str, str] = {
    IssueStatus.OPEN.value: "待处理",
    IssueStatus.RESOLVED.value: "已处置",
}

TASK_MODE_LABELS: dict[str, str] = {
    TaskMode.INGEST.value: "采集",
    TaskMode.PARSE.value: "解析",
    TaskMode.BOTH.value: "采集 + 解析",
}

TASK_STATUS_LABELS: dict[str, str] = {
    TaskStatus.QUEUED.value: "排队中",
    TaskStatus.RUNNING.value: "运行中",
    TaskStatus.SUCCESS.value: "成功",
    TaskStatus.FAILED.value: "失败",
}

ROLE_LABELS: dict[str, str] = {
    Role.ADMIN.value: "运营主管",
    Role.ANALYST.value: "内容运营",
    Role.VIEWER.value: "剪辑师（只读）",
}

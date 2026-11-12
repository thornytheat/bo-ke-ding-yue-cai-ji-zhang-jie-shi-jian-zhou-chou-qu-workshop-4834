"""算法阈值与跑批约束常量（口径集中，禁止散落在 service 里）。"""
from __future__ import annotations

RATE_WINDOW_SECONDS = 60

# ---- 算法 1：时间戳解析 ----
# 「约 N 分钟处」这类模糊表述的置信度（人工需复核）
CONFIDENCE_ABOUT_MINUTES = 0.62
CONFIDENCE_HHMMSS = 0.95
CONFIDENCE_MMSS = 0.86
CONFIDENCE_CN_CLOCK = 0.90
CONFIDENCE_AT = 0.88
CONFIDENCE_NO_TITLE_PENALTY = 0.05

# 单集时长 ≥ 60 分钟时，裸 "M:SS" 才存在「也可读成 H:MM」的歧义
AMBIGUOUS_MIN_DURATION_SECONDS = 3600

# ---- 算法 2：章节窗口不变量 ----
# 相邻章节缺口超过 8 分钟 → gap_warning
GAP_WARNING_SECONDS = 8 * 60
# 章节窗口短于 20 秒 → 折叠进前一章
SHORT_CHAPTER_SECONDS = 20
# 两个章节时间点相同（或差 ≤ 该容差）视为重叠，保留置信高者并合并标题
OVERLAP_TOLERANCE_SECONDS = 0

# ---- 写入约束 ----
MAX_CHAPTERS_PER_EPISODE = 80
MAX_SHOW_NOTES_CHARS = 20000
MAX_TITLE_CHARS = 120

# ---- 列表分页 ----
DEFAULT_PAGE_SIZE = 24
MAX_PAGE_SIZE = 200

# ---- 导出 ----
EXPORT_BOM = "\ufeff"

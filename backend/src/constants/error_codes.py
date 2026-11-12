"""统一错误码，前端 utils/errorMessage.ts 兜底文案与之对应。"""
from __future__ import annotations

ERROR_CODES: dict[str, str] = {
    "AUTH_INVALID": "邮箱或密码不正确",
    "AUTH_MISSING": "缺少或无效的访问令牌",
    "FORBIDDEN": "当前角色无权执行该操作",
    "NOT_FOUND": "对象不存在",
    "CONFLICT": "对象状态冲突",
    "RATE_LIMITED": "请求过于频繁，请稍后再试",
    "VALIDATION": "请求参数不合法",
    "EPISODE_LOCKED": "该单集正在被采集任务占用，稍后再试",
    "CHAPTER_NOT_FOUND": "章节不存在",
    "CHAPTER_OUT_OF_RANGE": "时间点超出单集时长",
    "CHAPTER_DUPLICATE": "同一时间点已存在章节",
    "TASK_BUSY": "已有采集/解析批次在运行，请等待完成",
    "FEED_INACTIVE": "订阅源已停用，无法运行采集",
    "EXPORT_EMPTY": "没有可导出的单集",
    "SEED_ONLY": "该操作仅用于演示数据初始化",
    "INTERNAL": "服务内部错误",
}

"""内容指纹：平台侧一次内容变更算一个 hash，采集时只比对指纹就知道是新增/更新/不变。"""
from __future__ import annotations

import hashlib


def episode_fingerprint(title: str, summary: str, duration_seconds: int, show_notes: str) -> str:
    payload = "\x1f".join(
        [
            (title or "").strip(),
            (summary or "").strip(),
            str(int(duration_seconds or 0)),
            (show_notes or "").strip(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

"""pytest 引导：容器内 pytest 从 /app 运行，本地直接从 backend/ 运行都能 import src。"""
from __future__ import annotations

import pathlib
import sys

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

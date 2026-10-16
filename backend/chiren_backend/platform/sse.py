"""SSE 事件格式化辅助函数。"""

import json
from typing import Any


def make_sse_event(event: str, data: dict[str, Any] | None = None) -> dict[str, str]:
    """构建 server-sent event 负载。"""
    return {"event": event, "data": json.dumps(data or {}, ensure_ascii=False)}

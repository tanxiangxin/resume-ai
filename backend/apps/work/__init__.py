"""Work 应用入口。"""

from apps.work.router import router
from apps.work.service import cleanup_work

__all__ = ["cleanup_work", "router"]

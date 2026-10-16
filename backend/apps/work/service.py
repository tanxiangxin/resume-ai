"""Work 业务服务层。"""

from sqlalchemy import and_, delete, or_

from chiren_backend.platform.db import async_session
from chiren_backend.platform.models import BaseWork


async def cleanup_work() -> int:
    """清理启动时不需要保留的 work 记录。

    删除逻辑：
    - 删除 status 不等于 'error' 的所有记录（保留错误状态记录）
    - 删除 status 为 'error' 且 task_type 为 'jd_score' 的记录

    Returns:
        被删除的记录总数。
    """
    async with async_session() as session:
        stmt = delete(BaseWork).where(
            or_(
                BaseWork.status.is_(None),
                BaseWork.status != "error",
                and_(
                    BaseWork.status == "error",
                    BaseWork.task_type == "jd_score",
                ),
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

"""数据库引擎和会话依赖。"""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from chiren_backend.platform.models import Base

db_path = Path(__file__).parents[2] / "app.db"
engine = create_async_engine(
    f"sqlite+aiosqlite:///{db_path}",
    connect_args={"timeout": 30},
)


@event.listens_for(engine.sync_engine, "connect")
def _configure_sqlite_connection(dbapi_connection: Any, _: Any) -> None:
    """Configure waiting behavior without changing persistent journal state."""
    cursor = dbapi_connection.cursor()
    try:
        # Journal mode is persistent database state. Changing it while another
        # connection is reading or writing requires an exclusive lock, so it
        # must not be attempted for every pooled connection. The existing
        # database may legitimately be in WAL mode.
        cursor.execute("PRAGMA busy_timeout=30000")
    finally:
        cursor.close()

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

SQLITE_INDEXES: tuple[str, ...] = (
    """
    CREATE INDEX IF NOT EXISTS ix_work_task_status_meta_resume_id
    ON work (task_type, status, json_extract(meta_info, '$.resume_id'))
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_work_task_status_meta_round_id
    ON work (task_type, status, json_extract(meta_info, '$.round_id'))
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_work_task_status_meta_collection_id
    ON work (task_type, status, json_extract(meta_info, '$.collection_id'))
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_work_task_status_meta_source_hash
    ON work (task_type, status, json_extract(meta_info, '$.source_hash'))
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_greeting_batches_resume_source_status
    ON greeting_generation_batches (resume_id, source_hash, status)
    """,
)


async def init_db() -> None:
    """初始化数据库表。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for statement in SQLITE_INDEXES:
            await conn.execute(text(statement))


async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    """为 FastAPI 依赖注入提供数据库会话。"""
    async with async_session() as session:
        yield session

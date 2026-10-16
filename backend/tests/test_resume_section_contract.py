"""简历区块接口契约测试。"""

import asyncio
from typing import Any

from apps.resume_section.router import get_by_resumeid


class _EmptyScalars:
    def all(self) -> list[Any]:
        return []


class _EmptyResult:
    def scalars(self) -> _EmptyScalars:
        return _EmptyScalars()


class _CapturingSession:
    def __init__(self) -> None:
        self.statement: Any = None

    async def execute(self, statement: Any) -> _EmptyResult:
        self.statement = statement
        return _EmptyResult()


def test_resume_sections_are_queried_by_sort_order() -> None:
    """确保前端编辑器读取区块时拿到稳定排序。"""

    async def run_case() -> None:
        session = _CapturingSession()

        await get_by_resumeid("resume-1", session)  # type: ignore[arg-type]

        compiled = str(session.statement)
        assert "ORDER BY resume_sections.sort_order ASC" in compiled
        assert "resume_sections.id ASC" in compiled

    asyncio.run(run_case())

"""SSE 客户端使用的内存任务事件中心。"""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from shared.types.task import TaskStatus, TaskType

tasks: dict[str, dict[str, Any]] = {}
task_events: dict[str, asyncio.Queue] = {}


class TaskEventHub:
    """任务事件中心，负责状态更新和 SSE 订阅。"""

    def __init__(self) -> None:
        self._tasks = tasks
        self._events = task_events

    def create(
        self,
        task_id: str,
        task_type: TaskType,
        initial_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """创建内存任务记录。"""
        task_data = {
            "task_id": task_id,
            "task_type": task_type.value,
            "status": TaskStatus.PENDING,
            "result": None,
            "error": None,
        }
        if initial_data:
            task_data.update(initial_data)
        self._tasks[task_id] = task_data
        self._events[task_id] = asyncio.Queue()
        return self._tasks[task_id]

    async def emit(self, task_id: str, event: str, data: Any) -> None:
        """发送事件并更新内存任务快照。"""
        if task_id in self._tasks:
            if event == "status":
                self._tasks[task_id]["status"] = data
            elif event == "result":
                self._tasks[task_id]["result"] = data
            elif event == "error":
                self._tasks[task_id]["error"] = data
        if task_id in self._events:
            await self._events[task_id].put(
                {
                    "event": event,
                    "data": json.dumps(
                        {
                            "content": data,
                            "type": self._tasks[task_id]["task_type"],
                        },
                        ensure_ascii=False,
                    ),
                }
            )

    async def subscribe(self, task_id: str) -> AsyncIterator[dict[str, Any]]:
        """持续产出任务事件，直到任务进入终态。"""
        queue = self._events.get(task_id)
        if not queue:
            return
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=60)
                yield event
                if event["event"] in ("result", "error"):
                    break
            except TimeoutError:
                yield {"event": "heartbeat", "data": ""}
            except asyncio.CancelledError:
                raise

    async def cleanup(
        self,
        task_id: str,
        cleanup_fn: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """等待客户端消费后移除任务状态。"""
        await asyncio.sleep(120)
        if cleanup_fn:
            await cleanup_fn()
        self._tasks.pop(task_id, None)
        self._events.pop(task_id, None)


hub = TaskEventHub()


def create_task(
    task_id: str, task_type: TaskType, initial_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """创建内存任务记录。"""
    return hub.create(task_id, task_type, initial_data)


async def update_task_status(task_id: str, status: TaskStatus) -> None:
    """发布任务状态更新。"""
    await hub.emit(task_id, "status", status.value)


async def update_task_result(task_id: str, result: dict) -> None:
    """发布任务成功结果。"""
    await hub.emit(task_id, "status", TaskStatus.SUCCESS.value)
    await hub.emit(task_id, "result", json.dumps(result, ensure_ascii=False))


async def update_task_error(task_id: str, error: str) -> None:
    """发布任务失败结果。"""
    await hub.emit(task_id, "status", TaskStatus.ERROR.value)
    await hub.emit(task_id, "error", error)


async def cleanup_task(
    task_id: str,
    cleanup_fn: Callable[[], Awaitable[None]] | None = None,
) -> None:
    """清理内存任务记录。"""
    await hub.cleanup(task_id, cleanup_fn)

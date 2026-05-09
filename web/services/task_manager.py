"""
Background task manager for tracking download/dedup/upload tasks
"""
import asyncio
import logging
from enum import Enum
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: UUID
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    logs: list = field(default_factory=list)
    result: Any = None
    error: Optional[str] = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)

    def to_dict(self):
        return {
            "task_id": str(self.id),
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "logs": self.logs[-100:] if self.logs else [],
            "result": self.result,
            "error": self.error
        }


class TaskManager:
    """Centralized task manager for all background operations"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks = {}
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_tasks'):
            self._tasks: Dict[UUID, Task] = {}
            self._lock = asyncio.Lock()

    async def create_task(self, name: str) -> UUID:
        """Create a new task and return its ID"""
        task_id = uuid4()
        async with self._lock:
            self._tasks[task_id] = Task(id=task_id, name=name)
        logger.info(f"Created task {task_id} ({name})")
        return task_id

    async def get_task(self, task_id: UUID) -> Optional[Task]:
        """Get task by ID"""
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_progress(self, task_id: UUID, progress: int = None, log: str = None):
        """Update task progress and/or add log"""
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if progress is not None:
                    task.progress = progress
                if log:
                    task.logs.append(log)

    async def set_status(self, task_id: UUID, status: TaskStatus, result: Any = None, error: str = None):
        """Set task final status"""
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = status
                task.result = result
                task.error = error
                logger.info(f"Task {task_id} ({task.name}) set to {status.value}")

    async def cancel_task(self, task_id: UUID):
        """Cancel a running task"""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].cancel_event.set()
                self._tasks[task_id].status = TaskStatus.CANCELLED
                logger.info(f"Task {task_id} cancelled")

    async def is_cancelled(self, task_id: UUID) -> bool:
        """Check if task has been cancelled"""
        async with self._lock:
            if task_id in self._tasks:
                return self._tasks[task_id].cancel_event.is_set()
        return False

    def get_all_tasks(self) -> Dict[UUID, Task]:
        """Get all tasks"""
        return self._tasks.copy()

    async def remove_task(self, task_id: UUID):
        """Remove a task"""
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]


# Global instance
task_manager = TaskManager()

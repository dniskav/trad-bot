#!/usr/bin/env python3
"""
Queue Service
Lightweight async queue system for position management
"""

import asyncio
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from shared.logger import get_logger

log = get_logger("queue_service")


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueueTask:
    id: str
    task_type: str
    data: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class QueueService:
    """
    Lightweight async queue system for position management
    """

    def __init__(self, max_workers: int = 3, max_queue_size: int = 100):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.queue: Optional[asyncio.Queue] = None
        self.tasks: Dict[str, QueueTask] = {}
        self.workers: list[asyncio.Task] = []
        self.handlers: Dict[str, Callable] = {}
        self.running = False
        self._lock: Optional[asyncio.Lock] = None

    async def start(self):
        """Start the queue service"""
        if self.running:
            return

        # Initialize queue and lock in the current event loop
        self.queue = asyncio.Queue(maxsize=self.max_queue_size)
        self._lock = asyncio.Lock()

        self.running = True
        log.info(f"🚀 Starting Queue Service with {self.max_workers} workers")

        # Start worker tasks in the current event loop
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        log.info("✅ Queue Service started")

    async def stop(self):
        """Stop the queue service"""
        if not self.running:
            return

        self.running = False
        log.info("🛑 Stopping Queue Service...")

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

        log.info("✅ Queue Service stopped")

    def register_handler(self, task_type: str, handler: Callable):
        """Register a handler for a specific task type"""
        self.handlers[task_type] = handler
        log.info(f"📝 Registered handler for task type: {task_type}")

    async def enqueue(
        self, task_type: str, data: Dict[str, Any], max_retries: int = 3
    ) -> str:
        """Enqueue a new task"""
        if not self.running or not self.queue or not self._lock:
            raise RuntimeError("Queue service is not running")

        if self.queue.qsize() >= self.max_queue_size:
            raise RuntimeError(f"Queue is full (max: {self.max_queue_size})")

        task_id = str(uuid.uuid4())
        task = QueueTask(
            id=task_id, task_type=task_type, data=data, max_retries=max_retries
        )

        async with self._lock:
            self.tasks[task_id] = task

        await self.queue.put(task)
        log.info(f"📥 Enqueued task {task_id} of type {task_type}")

        return task_id

    async def get_task_status(self, task_id: str) -> Optional[QueueTask]:
        """Get the status of a task"""
        if not self._lock:
            return None
        async with self._lock:
            return self.tasks.get(task_id)

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        if not self._lock or not self.queue:
            return {
                "queue_size": 0,
                "max_queue_size": self.max_queue_size,
                "max_workers": self.max_workers,
                "running": self.running,
                "tasks": {
                    "pending": 0,
                    "processing": 0,
                    "completed": 0,
                    "failed": 0,
                    "total": 0,
                },
            }

        async with self._lock:
            pending = sum(
                1 for t in self.tasks.values() if t.status == TaskStatus.PENDING
            )
            processing = sum(
                1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING
            )
            completed = sum(
                1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED
            )
            failed = sum(
                1 for t in self.tasks.values() if t.status == TaskStatus.FAILED
            )

        return {
            "queue_size": self.queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "max_workers": self.max_workers,
            "running": self.running,
            "tasks": {
                "pending": pending,
                "processing": processing,
                "completed": completed,
                "failed": failed,
                "total": len(self.tasks),
            },
        }

    async def _worker(self, worker_name: str):
        """Worker coroutine that processes tasks from the queue"""
        log.info(f"👷 Worker {worker_name} started")

        while self.running and self.queue:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                # Process the task
                await self._process_task(task, worker_name)

            except asyncio.TimeoutError:
                # No tasks available, continue
                continue
            except asyncio.CancelledError:
                log.info(f"👷 Worker {worker_name} cancelled")
                break
            except Exception as e:
                log.error(f"❌ Worker {worker_name} error: {e}")

        log.info(f"👷 Worker {worker_name} stopped")

    async def _process_task(self, task: QueueTask, worker_name: str):
        """Process a single task"""
        log.info(
            f"🔄 Worker {worker_name} processing task {task.id} ({task.task_type})"
        )

        # Update task status
        if self._lock:
            async with self._lock:
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.now(timezone.utc)

        try:
            # Get handler for task type
            handler = self.handlers.get(task.task_type)
            if not handler:
                raise ValueError(
                    f"No handler registered for task type: {task.task_type}"
                )

            # Execute the handler
            result = await handler(task.data)

            # Update task status
            if self._lock:
                async with self._lock:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now(timezone.utc)
                    task.result = result

            log.info(f"✅ Worker {worker_name} completed task {task.id}")

        except Exception as e:
            # Handle task failure
            if self._lock and self.queue:
                async with self._lock:
                    task.retry_count += 1
                    task.error = str(e)

                    if task.retry_count < task.max_retries:
                        # Retry the task
                        task.status = TaskStatus.PENDING
                        task.started_at = None
                        await self.queue.put(task)
                        log.warning(
                            f"🔄 Worker {worker_name} retrying task {task.id} (attempt {task.retry_count})"
                        )
                    else:
                        # Mark as failed
                        task.status = TaskStatus.FAILED
                        task.completed_at = datetime.now(timezone.utc)
                        log.error(
                            f"❌ Worker {worker_name} failed task {task.id} after {task.max_retries} retries: {e}"
                        )


# Global queue service instance
queue_service = QueueService(max_workers=3, max_queue_size=100)

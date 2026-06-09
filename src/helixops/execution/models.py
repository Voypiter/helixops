"""Task execution models and event definitions."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class ExecutionEventType(Enum):
    """Types of execution events."""

    TASK_PENDING = "task.pending"
    TASK_READY = "task.ready"
    TASK_RUNNING = "task.running"
    TASK_SUCCEEDED = "task.succeeded"
    TASK_FAILED = "task.failed"
    TASK_RETRYING = "task.retrying"
    TASK_SKIPPED = "task.skipped"
    TASK_CANCELLED = "task.cancelled"
    TASK_TIMED_OUT = "task.timed_out"
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"


@dataclass
class TaskSimulationConfig:
    """Configuration for task simulation behavior."""

    task_id: str
    duration_ms: int = 100
    fail_probability: float = 0.0
    fail_message: str | None = None
    output_payload: dict[str, Any] = field(default_factory=dict)
    timeout_ms: int | None = None
    should_skip: bool = False

    def __post_init__(self) -> None:
        if self.duration_ms < 0:
            raise ValueError(f"duration_ms must be non-negative, got {self.duration_ms}")
        if not (0 <= self.fail_probability <= 1):
            raise ValueError(f"fail_probability must be in [0, 1], got {self.fail_probability}")
        if self.timeout_ms is not None and self.timeout_ms <= 0:
            raise ValueError(f"timeout_ms must be positive, got {self.timeout_ms}")


@dataclass
class ExecutionEvent:
    """A single execution event in the timeline."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: ExecutionEventType = ExecutionEventType.TASK_PENDING
    timestamp: datetime = field(default_factory=datetime.utcnow)
    run_id: str = ""
    task_id: str | None = None
    attempt_id: str | None = None
    duration_ms: float | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id cannot be empty")


@dataclass
class TaskExecutionResult:
    """Result of a single task execution."""

    task_id: str
    attempt_id: str
    succeeded: bool
    duration_ms: float
    error_message: str | None = None
    output_payload: dict[str, Any] = field(default_factory=dict)
    timed_out: bool = False
    was_cancelled: bool = False
    was_skipped: bool = False


@dataclass
class RunExecutionResult:
    """Complete result of a workflow run."""

    run_id: str
    workflow_id: str
    succeeded: bool
    total_duration_ms: float
    task_results: dict[str, TaskExecutionResult] = field(default_factory=dict)
    events: list[ExecutionEvent] = field(default_factory=list)
    error_message: str | None = None
    was_cancelled: bool = False

    def get_task_result(self, task_id: str) -> TaskExecutionResult | None:
        """Get the result for a specific task."""
        return self.task_results.get(task_id)

    def failed_tasks(self) -> list[str]:
        """Get all failed task IDs."""
        return [
            task_id
            for task_id, result in self.task_results.items()
            if not result.succeeded and not result.was_skipped
        ]

    def successful_tasks(self) -> list[str]:
        """Get all successful task IDs."""
        return [task_id for task_id, result in self.task_results.items() if result.succeeded]

    def skipped_tasks(self) -> list[str]:
        """Get all skipped task IDs."""
        return [task_id for task_id, result in self.task_results.items() if result.was_skipped]

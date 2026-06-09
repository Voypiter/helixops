"""Core domain models for HelixOps."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class TaskState(Enum):
    """Enumeration of valid task states."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class FailureMode(Enum):
    """Types of synthetic failures that can be injected."""

    CRASH = "crash"
    TIMEOUT = "timeout"
    TRANSIENT_ERROR = "transient_error"
    POISON = "poison"
    SLOW = "slow"
    PARTIAL_WRITE = "partial_write"


@dataclass
class RetryPolicy:
    """Policy governing task retry behavior."""

    max_attempts: int = 3
    initial_backoff_ms: int = 100
    max_backoff_ms: int = 30000
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            from helixops.domain.errors import InvalidRetryPolicyError

            raise InvalidRetryPolicyError(f"max_attempts must be >= 1, got {self.max_attempts}")
        if self.initial_backoff_ms < 0:
            from helixops.domain.errors import InvalidRetryPolicyError

            raise InvalidRetryPolicyError(
                f"initial_backoff_ms must be >= 0, got {self.initial_backoff_ms}"
            )
        if self.max_backoff_ms < self.initial_backoff_ms:
            from helixops.domain.errors import InvalidRetryPolicyError

            raise InvalidRetryPolicyError(
                f"max_backoff_ms ({self.max_backoff_ms}) must be >= "
                f"initial_backoff_ms ({self.initial_backoff_ms})"
            )
        if self.backoff_multiplier <= 1.0:
            from helixops.domain.errors import InvalidRetryPolicyError

            raise InvalidRetryPolicyError(
                f"backoff_multiplier must be > 1.0, got {self.backoff_multiplier}"
            )
        if not 0 <= self.jitter_factor <= 1.0:
            from helixops.domain.errors import InvalidRetryPolicyError

            raise InvalidRetryPolicyError(
                f"jitter_factor must be in [0, 1.0], got {self.jitter_factor}"
            )


@dataclass
class FailureProfile:
    """Definition of synthetic failures to inject into a task."""

    task_id: str
    failure_mode: FailureMode
    probability: float = 0.1
    delay_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0 <= self.probability <= 1):
            from helixops.domain.errors import ValidationError

            raise ValidationError(f"probability must be in [0, 1], got {self.probability}")
        if self.delay_ms < 0:
            from helixops.domain.errors import ValidationError

            raise ValidationError(f"delay_ms must be >= 0, got {self.delay_ms}")


@dataclass
class TaskNode:
    """Represents a single task in a workflow."""

    task_id: str
    name: str
    timeout_seconds: int | None = None
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    depends_on: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id or not self.task_id.strip():
            from helixops.domain.errors import ValidationError

            raise ValidationError("task_id cannot be empty")
        if not self.name or not self.name.strip():
            from helixops.domain.errors import ValidationError

            raise ValidationError("name cannot be empty")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            from helixops.domain.errors import InvalidTimeoutError

            raise InvalidTimeoutError(f"timeout_seconds must be > 0, got {self.timeout_seconds}")


@dataclass
class DependencyGraph:
    """Represents the dependency relationships between tasks."""

    tasks: dict[str, TaskNode] = field(default_factory=dict)

    def add_task(self, task: TaskNode) -> None:
        """Add a task to the graph."""
        if task.task_id in self.tasks:
            from helixops.domain.errors import DuplicateTaskError

            raise DuplicateTaskError(
                f"Task with ID '{task.task_id}' already exists in the workflow"
            )
        self.tasks[task.task_id] = task

    def validate(self) -> None:
        """Validate the entire dependency graph."""
        self._validate_references()
        self._validate_no_cycles()

    def _validate_references(self) -> None:
        """Ensure all dependencies reference existing tasks."""
        for task_id, task in self.tasks.items():
            for dep_id in task.depends_on:
                if dep_id not in self.tasks:
                    from helixops.domain.errors import MissingDependencyError

                    raise MissingDependencyError(
                        f"Task '{task_id}' depends on non-existent task '{dep_id}'"
                    )

    def _validate_no_cycles(self) -> None:
        """Detect cycles in the dependency graph."""
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            for neighbor in self.tasks[task_id].depends_on:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task_id in self.tasks:
            if task_id not in visited and has_cycle(task_id):
                from helixops.domain.errors import CyclicDependencyError

                raise CyclicDependencyError("Workflow contains cyclic dependencies")


@dataclass
class TaskAttempt:
    """Represents a single attempt to execute a task."""

    attempt_id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    state: TaskState = TaskState.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_duration_ms(self) -> float | None:
        """Get the duration of this attempt in milliseconds."""
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds() * 1000

    def mark_succeeded(self) -> None:
        """Transition to SUCCEEDED state."""
        from helixops.domain.errors import IllegalStateTransitionError

        if self.state in (TaskState.SUCCEEDED, TaskState.FAILED):
            raise IllegalStateTransitionError(
                f"Cannot transition from {self.state.value} to SUCCEEDED"
            )
        self.state = TaskState.SUCCEEDED
        self.completed_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        """Transition to FAILED state."""
        from helixops.domain.errors import IllegalStateTransitionError

        if self.state in (TaskState.SUCCEEDED, TaskState.FAILED):
            raise IllegalStateTransitionError(
                f"Cannot transition from {self.state.value} to FAILED"
            )
        self.state = TaskState.FAILED
        self.error_message = error
        self.completed_at = datetime.utcnow()

    def mark_running(self) -> None:
        """Transition to RUNNING state."""
        from helixops.domain.errors import IllegalStateTransitionError

        if self.state != TaskState.READY:
            raise IllegalStateTransitionError(
                f"Cannot transition from {self.state.value} to RUNNING"
            )
        self.state = TaskState.RUNNING
        self.started_at = datetime.utcnow()


@dataclass
class ExecutionRun:
    """Represents a single execution of a workflow."""

    run_id: str = field(default_factory=lambda: str(uuid4()))
    workflow_id: str = ""
    state: TaskState = TaskState.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    task_attempts: dict[str, list[TaskAttempt]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_task_attempt(self, attempt: TaskAttempt) -> None:
        """Record a new task attempt."""
        if attempt.task_id not in self.task_attempts:
            self.task_attempts[attempt.task_id] = []
        self.task_attempts[attempt.task_id].append(attempt)

    def get_task_attempts(self, task_id: str) -> list[TaskAttempt]:
        """Get all attempts for a task."""
        return self.task_attempts.get(task_id, [])

    def get_latest_attempt(self, task_id: str) -> TaskAttempt | None:
        """Get the most recent attempt for a task."""
        attempts = self.get_task_attempts(task_id)
        return attempts[-1] if attempts else None

    def get_duration_ms(self) -> float | None:
        """Get the total duration of this run in milliseconds."""
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds() * 1000


@dataclass
class EventLog:
    """Log of domain events during execution."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: str = ""
    run_id: str = ""
    task_id: str | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryPlan:
    """Plan for recovering from an incomplete run."""

    recovery_id: str = field(default_factory=lambda: str(uuid4()))
    run_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    failed_tasks: list[str] = field(default_factory=list)
    recoverable_tasks: list[str] = field(default_factory=list)
    completed_tasks: list[str] = field(default_factory=list)
    audit_trail: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_audit_entry(self, entry: str) -> None:
        """Add an entry to the audit trail."""
        self.audit_trail.append(f"[{datetime.utcnow().isoformat()}] {entry}")


@dataclass
class Workflow:
    """A complete workflow definition with tasks and dependencies."""

    workflow_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    graph: DependencyGraph = field(default_factory=DependencyGraph)
    failure_profiles: list[FailureProfile] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            from helixops.domain.errors import ValidationError

            raise ValidationError("Workflow name cannot be empty")

    def add_task(self, task: TaskNode) -> None:
        """Add a task to the workflow."""
        self.graph.add_task(task)

    def validate(self) -> None:
        """Validate the entire workflow."""
        self.graph.validate()
        self._validate_failure_profiles()

    def _validate_failure_profiles(self) -> None:
        """Validate that all failure profiles reference existing tasks."""
        for profile in self.failure_profiles:
            if profile.task_id not in self.graph.tasks:
                from helixops.domain.errors import MissingDependencyError

                raise MissingDependencyError(
                    f"Failure profile references non-existent task '{profile.task_id}'"
                )

    def get_task(self, task_id: str) -> TaskNode | None:
        """Retrieve a task by ID."""
        return self.graph.tasks.get(task_id)

    def get_all_tasks(self) -> list[TaskNode]:
        """Get all tasks in the workflow."""
        return list(self.graph.tasks.values())

    def get_task_count(self) -> int:
        """Get the total number of tasks."""
        return len(self.graph.tasks)

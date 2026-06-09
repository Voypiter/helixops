"""Runtime metrics collection and analysis."""

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TaskMetrics:
    """Metrics for task execution."""

    task_id: str
    duration_ms: float
    succeeded: bool
    retry_count: int = 0
    skipped: bool = False
    error: str | None = None


@dataclass
class MetricsSnapshot:
    """Point-in-time snapshot of system metrics."""

    timestamp: datetime = field(default_factory=datetime.utcnow)
    task_count: int = 0
    succeeded_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    retry_count: int = 0
    total_duration_ms: float = 0.0
    avg_task_duration_ms: float = 0.0
    min_task_duration_ms: float = float("inf")
    max_task_duration_ms: float = 0.0
    p50_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0
    throughput_tasks_per_sec: float = 0.0

    def update_from_tasks(self, tasks: list[TaskMetrics]) -> None:
        """Update metrics from task list."""
        if not tasks:
            return

        self.task_count = len(tasks)
        self.succeeded_count = sum(1 for t in tasks if t.succeeded and not t.skipped)
        self.failed_count = sum(1 for t in tasks if not t.succeeded and not t.skipped)
        self.skipped_count = sum(1 for t in tasks if t.skipped)
        self.retry_count = sum(t.retry_count for t in tasks)

        durations = [t.duration_ms for t in tasks]
        self.total_duration_ms = sum(durations)
        self.avg_task_duration_ms = statistics.mean(durations)
        self.min_task_duration_ms = min(durations)
        self.max_task_duration_ms = max(durations)

        if len(durations) > 1:
            self.p50_duration_ms = statistics.median(durations)
            self.p99_duration_ms = sorted(durations)[int(len(durations) * 0.99)]
        else:
            self.p50_duration_ms = durations[0]
            self.p99_duration_ms = durations[0]

        if self.total_duration_ms > 0:
            self.throughput_tasks_per_sec = (self.task_count / self.total_duration_ms) * 1000


class MetricsCollector:
    """Collects and aggregates system metrics."""

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self.tasks: list[TaskMetrics] = []
        self.snapshots: list[MetricsSnapshot] = []

    def record_task(self, metrics: TaskMetrics) -> None:
        """Record task metrics."""
        self.tasks.append(metrics)

    def take_snapshot(self) -> MetricsSnapshot:
        """Take a snapshot of current metrics."""
        snapshot = MetricsSnapshot()
        snapshot.update_from_tasks(self.tasks)
        self.snapshots.append(snapshot)
        return snapshot

    def get_current_snapshot(self) -> MetricsSnapshot:
        """Get current metrics without storing snapshot."""
        snapshot = MetricsSnapshot()
        snapshot.update_from_tasks(self.tasks)
        return snapshot

    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        snapshot = self.get_current_snapshot()

        return {
            "task_count": snapshot.task_count,
            "succeeded_count": snapshot.succeeded_count,
            "failed_count": snapshot.failed_count,
            "skipped_count": snapshot.skipped_count,
            "retry_count": snapshot.retry_count,
            "total_duration_ms": snapshot.total_duration_ms,
            "avg_task_duration_ms": round(snapshot.avg_task_duration_ms, 2),
            "min_task_duration_ms": round(snapshot.min_task_duration_ms, 2),
            "max_task_duration_ms": round(snapshot.max_task_duration_ms, 2),
            "p50_duration_ms": round(snapshot.p50_duration_ms, 2),
            "p99_duration_ms": round(snapshot.p99_duration_ms, 2),
            "throughput_tasks_per_sec": round(snapshot.throughput_tasks_per_sec, 2),
        }

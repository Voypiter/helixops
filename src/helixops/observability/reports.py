"""Workflow execution reports and performance analysis."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskSummary:
    """Summary of task execution."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    retriable_failed: int = 0


@dataclass
class RetrySummary:
    """Summary of retry behavior."""

    total_retries: int = 0
    tasks_with_retries: int = 0
    avg_retries_per_task: float = 0.0


@dataclass
class PerformanceSummary:
    """Summary of performance metrics."""

    total_duration_ms: float = 0.0
    avg_task_duration_ms: float = 0.0
    critical_path_ms: float = 0.0
    parallelism_factor: float = 1.0


@dataclass
class Bottleneck:
    """Performance bottleneck."""

    task_id: str
    duration_ms: float
    reason: str


@dataclass
class WorkflowReport:
    """Comprehensive workflow execution report."""

    run_id: str = ""
    workflow_id: str = ""
    status: str = "UNKNOWN"
    created_at: str = ""
    completed_at: str | None = None
    duration_ms: float = 0.0
    task_summary: TaskSummary = field(default_factory=TaskSummary)
    retry_summary: RetrySummary = field(default_factory=RetrySummary)
    performance_summary: PerformanceSummary = field(default_factory=PerformanceSummary)
    bottlenecks: list[Bottleneck] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recovery_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "task_summary": {
                "total": self.task_summary.total,
                "succeeded": self.task_summary.succeeded,
                "failed": self.task_summary.failed,
                "skipped": self.task_summary.skipped,
            },
            "retry_summary": {
                "total_retries": self.retry_summary.total_retries,
                "tasks_with_retries": self.retry_summary.tasks_with_retries,
            },
            "warnings": self.warnings,
            "bottleneck_count": len(self.bottlenecks),
        }

    def to_text(self) -> str:
        """Generate human-readable report."""
        lines = [
            "HelixOps Workflow Report",
            "========================",
            f"Run ID: {self.run_id}",
            f"Status: {self.status}",
            f"Duration: {self.duration_ms}ms",
            "",
            "Task Summary:",
            f"  Total: {self.task_summary.total}",
            f"  Succeeded: {self.task_summary.succeeded}",
            f"  Failed: {self.task_summary.failed}",
            f"  Skipped: {self.task_summary.skipped}",
            "",
            "Retries:",
            f"  Total: {self.retry_summary.total_retries}",
            f"  Tasks with retries: {self.retry_summary.tasks_with_retries}",
        ]

        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  ⚠️  {warning}")

        if self.bottlenecks:
            lines.append("")
            lines.append("Bottlenecks:")
            for bottleneck in self.bottlenecks[:5]:
                lines.append(
                    f"  • {bottleneck.task_id}: {bottleneck.duration_ms}ms ({bottleneck.reason})"
                )

        return "\n".join(lines)

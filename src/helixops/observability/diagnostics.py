"""Performance diagnostics and bottleneck detection."""

from helixops.observability.metrics import TaskMetrics
from helixops.observability.reports import Bottleneck, WorkflowReport


class PerformanceDiagnostics:
    """Analyzes execution for performance issues."""

    @staticmethod
    def identify_bottlenecks(tasks: list[TaskMetrics], percentile: float = 0.9) -> list[Bottleneck]:
        """Identify slow tasks that are bottlenecks.

        Args:
            tasks: List of TaskMetrics
            percentile: Duration percentile threshold (default 0.9 = top 10%)

        Returns:
            List of Bottleneck objects
        """
        if not tasks:
            return []

        durations = sorted([t.duration_ms for t in tasks])
        threshold = durations[int(len(durations) * percentile)]

        bottlenecks = []
        for task in tasks:
            if task.duration_ms >= threshold:
                reason = "Slow task" if task.succeeded else "Slow failed task"
                bottlenecks.append(
                    Bottleneck(
                        task_id=task.task_id,
                        duration_ms=task.duration_ms,
                        reason=reason,
                    )
                )

        return sorted(bottlenecks, key=lambda b: b.duration_ms, reverse=True)

    @staticmethod
    def identify_retry_heavy_tasks(tasks: list[TaskMetrics], threshold: int = 2) -> list[str]:
        """Identify tasks with excessive retries.

        Args:
            tasks: List of TaskMetrics
            threshold: Retry count threshold (default 2 = 2+ retries)

        Returns:
            List of task IDs with excessive retries
        """
        return [t.task_id for t in tasks if t.retry_count >= threshold]

    @staticmethod
    def generate_warnings(tasks: list[TaskMetrics]) -> list[str]:
        """Generate warnings about execution issues.

        Args:
            tasks: List of TaskMetrics

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for high failure rate
        if tasks:
            failed = sum(1 for t in tasks if not t.succeeded)
            failure_rate = failed / len(tasks)
            if failure_rate > 0.1:
                warnings.append(f"High failure rate: {failure_rate * 100:.1f}%")

        # Check for excessive retries
        total_retries = sum(t.retry_count for t in tasks)
        if total_retries > len(tasks):
            warnings.append(f"Excessive retries: {total_retries} total retries")

        # Check for large duration variance
        durations = [t.duration_ms for t in tasks if t.duration_ms > 0]
        if len(durations) > 1:
            avg = sum(durations) / len(durations)
            max_duration = max(durations)
            if max_duration > avg * 10:
                warnings.append(
                    f"Large task duration variance: max is {max_duration / avg:.1f}x average"
                )

        return warnings


def analyze_workflow(report: WorkflowReport, tasks: list[TaskMetrics]) -> None:
    """Analyze workflow and populate report with diagnostics.

    Args:
        report: WorkflowReport to populate
        tasks: List of TaskMetrics from execution
    """
    diag = PerformanceDiagnostics()

    # Identify bottlenecks
    report.bottlenecks = diag.identify_bottlenecks(tasks)

    # Identify retry-heavy tasks
    retry_heavy = diag.identify_retry_heavy_tasks(tasks)
    if retry_heavy:
        report.warnings.append(f"{len(retry_heavy)} tasks had excessive retries")

    # Generate warnings
    report.warnings.extend(diag.generate_warnings(tasks))

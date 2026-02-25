"""Tests for observability, metrics, and reports."""

import pytest

from helixops.observability.metrics import MetricsCollector, TaskMetrics, MetricsSnapshot
from helixops.observability.health import HealthStatus, get_health_status
from helixops.observability.reports import WorkflowReport, TaskSummary, RetrySummary, PerformanceSummary


class TestMetricsCollector:
    """Tests for metrics collection."""

    def test_record_single_task(self) -> None:
        """Should record a single task."""
        collector = MetricsCollector()
        metrics = TaskMetrics(task_id="t1", duration_ms=100.0, succeeded=True)

        collector.record_task(metrics)

        assert len(collector.tasks) == 1
        assert collector.tasks[0].task_id == "t1"

    def test_metrics_snapshot(self) -> None:
        """Should compute metrics snapshot."""
        collector = MetricsCollector()
        for i in range(5):
            metrics = TaskMetrics(
                task_id=f"t{i}",
                duration_ms=100.0 + i * 10,
                succeeded=(i < 4),
            )
            collector.record_task(metrics)

        snapshot = collector.get_current_snapshot()

        assert snapshot.task_count == 5
        assert snapshot.succeeded_count == 4
        assert snapshot.failed_count == 1
        assert snapshot.total_duration_ms > 0

    def test_percentile_calculations(self) -> None:
        """Should calculate percentiles correctly."""
        collector = MetricsCollector()
        for i in range(100):
            collector.record_task(TaskMetrics(task_id=f"t{i}", duration_ms=float(i), succeeded=True))

        snapshot = collector.get_current_snapshot()

        assert snapshot.p50_duration_ms > 0
        assert snapshot.p99_duration_ms > snapshot.p50_duration_ms

    def test_throughput_calculation(self) -> None:
        """Should calculate throughput."""
        collector = MetricsCollector()
        for _ in range(10):
            collector.record_task(TaskMetrics(task_id="t", duration_ms=100.0, succeeded=True))

        snapshot = collector.get_current_snapshot()

        assert snapshot.throughput_tasks_per_sec > 0

    def test_metrics_summary(self) -> None:
        """Should generate summary."""
        collector = MetricsCollector()
        collector.record_task(TaskMetrics(task_id="t1", duration_ms=50.0, succeeded=True))
        collector.record_task(TaskMetrics(task_id="t2", duration_ms=100.0, succeeded=False, retry_count=2))

        summary = collector.get_summary()

        assert summary["task_count"] == 2
        assert summary["succeeded_count"] == 1
        assert summary["failed_count"] == 1
        assert summary["retry_count"] == 2


class TestHealthStatus:
    """Tests for health status."""

    def test_health_check_pass(self) -> None:
        """Should track passing checks."""
        health = HealthStatus()
        health.add_check("db_connection", True)
        health.add_check("storage_ready", True)

        assert health.status == "healthy"
        assert health.ready is True

    def test_health_check_fail(self) -> None:
        """Should mark as degraded when check fails."""
        health = HealthStatus()
        health.add_check("db_connection", True)
        health.add_check("storage_ready", False)

        assert health.status == "degraded"

    def test_get_health_status(self) -> None:
        """Should get current health status."""
        health = get_health_status()

        assert health.status in ["healthy", "degraded", "unhealthy"]
        assert "system_responsive" in health.checks


class TestWorkflowReport:
    """Tests for workflow reports."""

    def test_create_report(self) -> None:
        """Should create workflow report."""
        report = WorkflowReport(
            run_id="run-1",
            workflow_id="wf-1",
            status="SUCCEEDED",
            duration_ms=5000.0,
        )

        assert report.run_id == "run-1"
        assert report.status == "SUCCEEDED"

    def test_task_summary(self) -> None:
        """Should track task summary."""
        report = WorkflowReport(run_id="run-1", workflow_id="wf-1")
        report.task_summary = TaskSummary(
            total=10,
            succeeded=8,
            failed=2,
        )

        assert report.task_summary.total == 10
        assert report.task_summary.failed == 2

    def test_retry_summary(self) -> None:
        """Should track retry summary."""
        report = WorkflowReport(run_id="run-1", workflow_id="wf-1")
        report.retry_summary = RetrySummary(
            total_retries=5,
            tasks_with_retries=3,
        )

        assert report.retry_summary.total_retries == 5

    def test_report_to_dict(self) -> None:
        """Should convert report to dictionary."""
        report = WorkflowReport(
            run_id="run-1",
            workflow_id="wf-1",
            status="SUCCEEDED",
        )

        report_dict = report.to_dict()

        assert report_dict["run_id"] == "run-1"
        assert "task_summary" in report_dict

    def test_report_to_text(self) -> None:
        """Should generate human-readable report."""
        report = WorkflowReport(
            run_id="run-1",
            workflow_id="wf-1",
            status="SUCCEEDED",
            duration_ms=1000.0,
        )
        report.task_summary = TaskSummary(total=5, succeeded=5)
        report.warnings = ["Long-running task detected"]

        text = report.to_text()

        assert "run-1" in text
        assert "SUCCEEDED" in text
        assert "warnings" in text.lower()


class TestMetricsSnapshot:
    """Tests for metrics snapshot."""

    def test_empty_snapshot(self) -> None:
        """Should handle empty task list."""
        snapshot = MetricsSnapshot()
        snapshot.update_from_tasks([])

        assert snapshot.task_count == 0

    def test_single_task_snapshot(self) -> None:
        """Should calculate metrics for single task."""
        snapshot = MetricsSnapshot()
        task = TaskMetrics(task_id="t1", duration_ms=100.0, succeeded=True)
        snapshot.update_from_tasks([task])

        assert snapshot.task_count == 1
        assert snapshot.avg_task_duration_ms == 100.0
        assert snapshot.p50_duration_ms == 100.0

    def test_retry_counting(self) -> None:
        """Should count retries correctly."""
        collector = MetricsCollector()
        collector.record_task(TaskMetrics(task_id="t1", duration_ms=100.0, succeeded=True, retry_count=3))
        collector.record_task(TaskMetrics(task_id="t2", duration_ms=100.0, succeeded=True, retry_count=0))

        snapshot = collector.get_current_snapshot()

        assert snapshot.retry_count == 3

    def test_skipped_tasks(self) -> None:
        """Should count skipped tasks."""
        collector = MetricsCollector()
        collector.record_task(TaskMetrics(task_id="t1", duration_ms=0.0, succeeded=False, skipped=True))
        collector.record_task(TaskMetrics(task_id="t2", duration_ms=100.0, succeeded=True))

        snapshot = collector.get_current_snapshot()

        assert snapshot.skipped_count == 1
        assert snapshot.succeeded_count == 1


class TestPerformanceDiagnostics:
    """Tests for performance diagnostics."""

    def test_identify_bottlenecks(self) -> None:
        """Should identify slow tasks."""
        from helixops.observability.diagnostics import PerformanceDiagnostics

        tasks = [
            TaskMetrics(task_id="t1", duration_ms=10.0, succeeded=True),
            TaskMetrics(task_id="t2", duration_ms=50.0, succeeded=True),
            TaskMetrics(task_id="t3", duration_ms=100.0, succeeded=True),
            TaskMetrics(task_id="t4", duration_ms=200.0, succeeded=True),
        ]

        bottlenecks = PerformanceDiagnostics.identify_bottlenecks(tasks, percentile=0.75)

        assert len(bottlenecks) > 0
        assert bottlenecks[0].duration_ms == 200.0

    def test_identify_retry_heavy_tasks(self) -> None:
        """Should identify tasks with excessive retries."""
        from helixops.observability.diagnostics import PerformanceDiagnostics

        tasks = [
            TaskMetrics(task_id="t1", duration_ms=100.0, succeeded=True, retry_count=0),
            TaskMetrics(task_id="t2", duration_ms=100.0, succeeded=True, retry_count=5),
            TaskMetrics(task_id="t3", duration_ms=100.0, succeeded=True, retry_count=3),
        ]

        retry_heavy = PerformanceDiagnostics.identify_retry_heavy_tasks(tasks, threshold=2)

        assert len(retry_heavy) == 2
        assert "t2" in retry_heavy
        assert "t3" in retry_heavy

    def test_generate_warnings(self) -> None:
        """Should generate performance warnings."""
        from helixops.observability.diagnostics import PerformanceDiagnostics

        tasks = [
            TaskMetrics(task_id="t1", duration_ms=100.0, succeeded=False),
            TaskMetrics(task_id="t2", duration_ms=100.0, succeeded=False),
            TaskMetrics(task_id="t3", duration_ms=100.0, succeeded=True),
        ]

        warnings = PerformanceDiagnostics.generate_warnings(tasks)

        assert len(warnings) > 0
        assert any("failure" in w.lower() for w in warnings)

"""Tests for benchmarking infrastructure."""

import json

from helixops.benchmarks.harness import (
    BenchmarkResult,
    BenchmarkRunner,
    PerformanceMetrics,
    PerformanceThreshold,
)
from helixops.benchmarks.optimizations import (
    HotPathOptimizer,
    PerformanceTuning,
    PersistenceOptimizer,
    SchedulerOptimizer,
)


class TestBenchmarkRunner:
    """Tests for benchmark runner."""

    def test_runner_initialization(self) -> None:
        """Should initialize benchmark runner."""
        runner = BenchmarkRunner()

        assert len(runner.results) == 0
        assert len(runner.thresholds) == 0

    def test_add_threshold(self) -> None:
        """Should register performance thresholds."""
        runner = BenchmarkRunner()
        threshold = PerformanceThreshold(
            profile="balanced",
            max_duration_ms=5000.0,
            min_throughput_tasks_per_sec=10.0,
        )

        runner.add_threshold(threshold)

        assert "balanced" in runner.thresholds
        assert runner.thresholds["balanced"].max_duration_ms == 5000.0

    def test_run_benchmark(self) -> None:
        """Should execute benchmark."""
        import time

        def mock_execution():
            time.sleep(0.01)  # Simulate 10ms execution
            return PerformanceMetrics(
                scheduler_ms=100.0,
                storage_ms=50.0,
            )

        runner = BenchmarkRunner()
        result = runner.run_benchmark(
            profile="balanced",
            task_count=50,
            concurrency=5,
            execution_fn=mock_execution,
        )

        assert result.profile == "balanced"
        assert result.task_count == 50
        assert result.concurrency == 5
        assert result.throughput_tasks_per_sec > 0
        assert result.scheduler_overhead_ms == 100.0
        assert result.storage_overhead_ms == 50.0

    def test_benchmark_result_overhead_ratio(self) -> None:
        """Should calculate overhead ratio correctly."""
        result = BenchmarkResult(
            name="test",
            profile="balanced",
            task_count=50,
            concurrency=5,
            duration_ms=1000.0,
            throughput_tasks_per_sec=50.0,
            scheduler_overhead_ms=100.0,
            storage_overhead_ms=50.0,
        )

        # (100 + 50) / 1000 = 0.15
        assert abs(result.get_overhead_ratio() - 0.15) < 0.001

    def test_benchmark_result_meets_threshold(self) -> None:
        """Should check threshold compliance."""
        result = BenchmarkResult(
            name="test",
            profile="balanced",
            task_count=50,
            concurrency=5,
            duration_ms=1000.0,
            throughput_tasks_per_sec=50.0,
        )

        assert result.meets_threshold(max_duration_ms=2000.0, min_throughput=25.0)
        assert not result.meets_threshold(max_duration_ms=500.0, min_throughput=25.0)
        assert not result.meets_threshold(max_duration_ms=2000.0, min_throughput=100.0)

    def test_check_regression_no_threshold(self) -> None:
        """Should handle missing threshold."""
        runner = BenchmarkRunner()
        result = BenchmarkResult(
            name="test",
            profile="balanced",
            task_count=50,
            concurrency=5,
            duration_ms=1000.0,
            throughput_tasks_per_sec=50.0,
        )

        checks = runner.check_regression(result)

        assert checks["checked"] is False

    def test_check_regression_with_threshold(self) -> None:
        """Should detect regressions."""
        runner = BenchmarkRunner()
        threshold = PerformanceThreshold(
            profile="balanced",
            max_duration_ms=1500.0,
            min_throughput_tasks_per_sec=40.0,
        )
        runner.add_threshold(threshold)

        result = BenchmarkResult(
            name="test",
            profile="balanced",
            task_count=50,
            concurrency=5,
            duration_ms=1000.0,
            throughput_tasks_per_sec=50.0,
        )

        checks = runner.check_regression(result)

        assert checks["duration_ok"] is True
        assert checks["throughput_ok"] is True

    def test_get_summary_empty(self) -> None:
        """Should handle empty results."""
        runner = BenchmarkRunner()

        summary = runner.get_summary()

        assert summary["total_benchmarks"] == 0
        assert summary["avg_duration_ms"] == 0.0
        assert len(summary["regressions"]) == 0

    def test_get_summary_with_results(self) -> None:
        """Should aggregate results."""
        import time

        def mock_execution():
            time.sleep(0.01)  # Simulate 10ms execution
            return PerformanceMetrics()

        runner = BenchmarkRunner()
        runner.run_benchmark("balanced", 50, 5, mock_execution)
        runner.run_benchmark("balanced", 100, 10, mock_execution)

        summary = runner.get_summary()

        assert summary["total_benchmarks"] == 2
        assert summary["avg_duration_ms"] > 0
        assert summary["avg_throughput_tasks_per_sec"] > 0

    def test_export_results_json(self) -> None:
        """Should export results as JSON."""

        def mock_execution():
            return PerformanceMetrics(scheduler_ms=100.0)

        runner = BenchmarkRunner()
        runner.run_benchmark("balanced", 50, 5, mock_execution)

        export = runner.export_results(format="json")
        data = json.loads(export)

        assert "results" in data
        assert "summary" in data
        assert len(data["results"]) == 1

    def test_export_results_csv(self) -> None:
        """Should export results as CSV."""

        def mock_execution():
            return PerformanceMetrics()

        runner = BenchmarkRunner()
        runner.run_benchmark("balanced", 50, 5, mock_execution)

        export = runner.export_results(format="csv")

        assert "name,profile,task_count" in export
        assert "balanced" in export

    def test_export_results_text(self) -> None:
        """Should export results as text."""

        def mock_execution():
            return PerformanceMetrics()

        runner = BenchmarkRunner()
        runner.run_benchmark("balanced", 50, 5, mock_execution)

        export = runner.export_results(format="text")

        assert "Benchmark Results" in export
        assert "Duration:" in export


class TestSchedulerOptimizer:
    """Tests for scheduler optimizations."""

    def test_optimize_task_selection(self) -> None:
        """Should select highest priority ready tasks."""
        ready_tasks = ["t1", "t2", "t3", "t4", "t5"]
        priorities = {"t1": 1, "t2": 5, "t3": 2, "t4": 10, "t5": 3}

        selected = SchedulerOptimizer.optimize_task_selection(ready_tasks, priorities, 3)

        assert len(selected) == 3
        assert selected[0] == "t4"  # Priority 10
        assert selected[1] == "t2"  # Priority 5
        assert selected[2] == "t5"  # Priority 3

    def test_optimize_task_selection_respects_max(self) -> None:
        """Should respect max concurrent limit."""
        ready_tasks = ["t1", "t2", "t3"]
        priorities = {"t1": 1, "t2": 2, "t3": 3}

        selected = SchedulerOptimizer.optimize_task_selection(ready_tasks, priorities, 1)

        assert len(selected) == 1
        assert selected[0] == "t3"

    def test_optimize_dependency_check_satisfied(self) -> None:
        """Should pass when all dependencies complete."""
        dependencies = {"t2": {"t1"}, "t3": {"t1", "t2"}}
        completed = {"t1", "t2"}

        result = SchedulerOptimizer.optimize_dependency_check("t3", dependencies, completed)

        assert result is True

    def test_optimize_dependency_check_unsatisfied(self) -> None:
        """Should fail when dependencies missing."""
        dependencies = {"t2": {"t1"}, "t3": {"t1", "t2"}}
        completed = {"t1"}

        result = SchedulerOptimizer.optimize_dependency_check("t3", dependencies, completed)

        assert result is False

    def test_optimize_dependency_check_no_deps(self) -> None:
        """Should pass for tasks with no dependencies."""
        dependencies: dict = {}
        completed = set()

        result = SchedulerOptimizer.optimize_dependency_check("t1", dependencies, completed)

        assert result is True


class TestPersistenceOptimizer:
    """Tests for persistence optimizations."""

    def test_enable_batch_writes(self) -> None:
        """Should create batch write config."""
        config = PersistenceOptimizer.enable_batch_writes(batch_size=20)

        assert config.batch_storage is True
        assert config.batch_size == 20
        assert config.async_writes is True

    def test_enable_connection_pooling(self) -> None:
        """Should create pooling config."""
        config = PersistenceOptimizer.enable_connection_pooling(pool_size=30)

        assert config.connection_pooling is True
        assert config.pool_size == 30

    def test_estimate_io_savings(self) -> None:
        """Should estimate I/O improvement from batching."""
        savings = PersistenceOptimizer.estimate_io_savings(event_count=1000, batch_size=10)

        assert savings["unbatched_roundtrips"] == 1000
        assert savings["batched_roundtrips"] == 100
        assert savings["roundtrips_saved"] == 900
        assert savings["estimated_time_saved_ms"] == 9000.0
        assert savings["throughput_improvement_percent"] > 0


class TestHotPathOptimizer:
    """Tests for hot path optimizations."""

    def test_optimize_state_transitions(self) -> None:
        """Should measure state transition overhead."""
        duration_ms = HotPathOptimizer.optimize_state_transitions("t1", "PENDING", "READY")

        assert isinstance(duration_ms, float)
        assert duration_ms >= 0

    def test_optimize_event_persistence_without_batching(self) -> None:
        """Should estimate persistence overhead without batching."""
        overhead = HotPathOptimizer.optimize_event_persistence(100, with_batching=False)

        assert overhead["event_processing_ms"] == 50.0  # 100 * 0.5
        assert overhead["roundtrip_overhead_ms"] == 1000.0  # 100 * 10
        assert overhead["total_storage_overhead_ms"] == 1050.0

    def test_optimize_event_persistence_with_batching(self) -> None:
        """Should estimate persistence overhead with batching."""
        overhead = HotPathOptimizer.optimize_event_persistence(100, with_batching=True)

        assert overhead["event_processing_ms"] == 50.0  # 100 * 0.5
        assert overhead["roundtrip_overhead_ms"] == 100.0  # 10 roundtrips * 10ms
        assert overhead["total_storage_overhead_ms"] == 150.0


class TestPerformanceTuning:
    """Tests for performance tuning recommendations."""

    def test_recommend_tuning_small_workflow(self) -> None:
        """Should recommend config for small workflows."""
        rec = PerformanceTuning.recommend_tuning(10)

        assert rec["profile"] == "small_workflows"
        assert rec["config"]["max_concurrent"] == 10
        assert rec["config"]["batch_size"] == 5

    def test_recommend_tuning_medium_workflow(self) -> None:
        """Should recommend config for medium workflows."""
        rec = PerformanceTuning.recommend_tuning(50)

        assert rec["profile"] == "medium_workflows"
        assert rec["config"]["max_concurrent"] == 50
        assert rec["config"]["batch_size"] == 10

    def test_recommend_tuning_large_workflow(self) -> None:
        """Should recommend config for large workflows."""
        rec = PerformanceTuning.recommend_tuning(200)

        assert rec["profile"] == "large_workflows"
        assert rec["config"]["max_concurrent"] == 200
        assert rec["config"]["batch_size"] == 50

    def test_recommend_tuning_high_throughput(self) -> None:
        """Should recommend config for high throughput."""
        rec = PerformanceTuning.recommend_tuning(1000)

        assert rec["profile"] == "high_throughput"
        assert rec["config"]["max_concurrent"] == 500
        assert rec["config"]["cache_enabled"] is True

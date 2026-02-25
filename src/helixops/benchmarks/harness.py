"""Deterministic benchmark harness for performance measurement."""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime


@dataclass
class PerformanceMetrics:
    """Raw performance measurements from execution."""

    scheduler_ms: float = 0.0
    storage_ms: float = 0.0
    retry_ms: float = 0.0
    recovery_ms: float = 0.0
    memory_peak_mb: Optional[float] = None
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of a benchmark execution."""

    name: str
    profile: str
    task_count: int
    concurrency: int
    duration_ms: float
    throughput_tasks_per_sec: float
    peak_memory_mb: Optional[float] = None
    scheduler_overhead_ms: float = 0.0
    storage_overhead_ms: float = 0.0
    retry_cost_ms: float = 0.0
    recovery_cost_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def get_overhead_ratio(self) -> float:
        """Calculate overhead ratio (overhead / total)."""
        total_overhead = self.scheduler_overhead_ms + self.storage_overhead_ms
        if self.duration_ms == 0:
            return 0.0
        return total_overhead / self.duration_ms

    def meets_threshold(self, max_duration_ms: float, min_throughput: float) -> bool:
        """Check if result meets thresholds."""
        return (
            self.duration_ms <= max_duration_ms
            and self.throughput_tasks_per_sec >= min_throughput
        )


@dataclass
class PerformanceThreshold:
    """Performance regression thresholds."""

    profile: str
    max_duration_ms: float
    min_throughput_tasks_per_sec: float
    max_overhead_ratio: float = 0.25  # 25% overhead acceptable


class BenchmarkRunner:
    """Deterministic benchmark runner for workflow execution."""

    def __init__(self):
        """Initialize benchmark runner."""
        self.results: List[BenchmarkResult] = []
        self.thresholds: Dict[str, PerformanceThreshold] = {}

    def add_threshold(self, threshold: PerformanceThreshold) -> None:
        """Register a performance threshold."""
        self.thresholds[threshold.profile] = threshold

    def run_benchmark(
        self,
        profile: str,
        task_count: int,
        concurrency: int,
        execution_fn: Callable[[], PerformanceMetrics],
        name: Optional[str] = None,
    ) -> BenchmarkResult:
        """Execute a deterministic benchmark.

        Args:
            profile: Workload profile name
            task_count: Number of tasks
            concurrency: Max concurrent tasks
            execution_fn: Function that runs and returns metrics
            name: Optional override for result name

        Returns:
            BenchmarkResult with measurements
        """
        if name is None:
            name = f"{profile}-{task_count}tasks-c{concurrency}"

        start_time = time.time()
        metrics = execution_fn()
        duration_ms = (time.time() - start_time) * 1000

        throughput = task_count / (duration_ms / 1000) if duration_ms > 0 else 0

        result = BenchmarkResult(
            name=name,
            profile=profile,
            task_count=task_count,
            concurrency=concurrency,
            duration_ms=duration_ms,
            throughput_tasks_per_sec=throughput,
            peak_memory_mb=metrics.memory_peak_mb,
            scheduler_overhead_ms=metrics.scheduler_ms,
            storage_overhead_ms=metrics.storage_ms,
            retry_cost_ms=metrics.retry_ms,
            recovery_cost_ms=metrics.recovery_ms,
        )

        self.results.append(result)
        return result

    def check_regression(self, result: BenchmarkResult) -> Dict[str, bool]:
        """Detect performance regressions.

        Returns:
            Dictionary with pass/fail for each dimension
        """
        threshold = self.thresholds.get(result.profile)
        if not threshold:
            return {"checked": False}

        return {
            "duration_ok": result.duration_ms <= threshold.max_duration_ms,
            "throughput_ok": result.throughput_tasks_per_sec >= threshold.min_throughput_tasks_per_sec,
            "overhead_ok": result.get_overhead_ratio() <= threshold.max_overhead_ratio,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get benchmark execution summary."""
        if not self.results:
            return {"total_benchmarks": 0, "avg_duration_ms": 0.0, "regressions": []}

        total = len(self.results)
        avg_duration = sum(r.duration_ms for r in self.results) / total
        avg_throughput = sum(r.throughput_tasks_per_sec for r in self.results) / total
        avg_overhead = sum(r.get_overhead_ratio() for r in self.results) / total

        regressions = []
        for result in self.results:
            checks = self.check_regression(result)
            if checks.get("checked", True):
                if not all(
                    checks.get(k, True) for k in ["duration_ok", "throughput_ok", "overhead_ok"]
                ):
                    regressions.append(result.name)

        return {
            "total_benchmarks": total,
            "avg_duration_ms": round(avg_duration, 2),
            "avg_throughput_tasks_per_sec": round(avg_throughput, 2),
            "avg_overhead_ratio": round(avg_overhead, 3),
            "regression_count": len(regressions),
            "regressions": regressions,
        }

    def export_results(self, format: str = "json") -> str:
        """Export benchmark results.

        Args:
            format: Export format (json, csv, text)

        Returns:
            Formatted results string
        """
        if format == "json":
            import json

            data = {
                "results": [
                    {
                        "name": r.name,
                        "profile": r.profile,
                        "task_count": r.task_count,
                        "concurrency": r.concurrency,
                        "duration_ms": round(r.duration_ms, 2),
                        "throughput_tasks_per_sec": round(r.throughput_tasks_per_sec, 2),
                        "overhead_ratio": round(r.get_overhead_ratio(), 3),
                        "timestamp": r.timestamp.isoformat(),
                    }
                    for r in self.results
                ],
                "summary": self.get_summary(),
            }
            return json.dumps(data, indent=2)

        elif format == "csv":
            lines = [
                "name,profile,task_count,concurrency,duration_ms,throughput,overhead_ratio"
            ]
            for r in self.results:
                lines.append(
                    f"{r.name},{r.profile},{r.task_count},{r.concurrency},"
                    f"{r.duration_ms:.2f},{r.throughput_tasks_per_sec:.2f},"
                    f"{r.get_overhead_ratio():.3f}"
                )
            return "\n".join(lines)

        else:
            lines = ["Benchmark Results", "=" * 60]
            for r in self.results:
                lines.append(f"\n{r.name}:")
                lines.append(f"  Duration: {r.duration_ms:.2f} ms")
                lines.append(f"  Throughput: {r.throughput_tasks_per_sec:.2f} tasks/sec")
                lines.append(f"  Overhead: {r.get_overhead_ratio() * 100:.1f}%")
            return "\n".join(lines)

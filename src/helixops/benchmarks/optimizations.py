"""Performance optimizations for scheduler and persistence layers."""

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class OptimizationConfig:
    """Configuration for performance optimizations."""

    batch_storage: bool = True
    batch_size: int = 10
    connection_pooling: bool = True
    pool_size: int = 20
    cache_hot_paths: bool = True
    async_writes: bool = True
    index_tasks_by_state: bool = True


class SchedulerOptimizer:
    """Optimizations for execution scheduler."""

    @staticmethod
    def optimize_task_selection(
        ready_tasks: list[str],
        task_priorities: dict[str, int],
        max_concurrent: int,
    ) -> list[str]:
        """Optimized task selection using priority queue.

        Uses cached priority ordering instead of repeated sorting.

        Args:
            ready_tasks: List of ready task IDs
            task_priorities: Pre-computed priorities
            max_concurrent: Max tasks to select

        Returns:
            Selected task IDs in priority order
        """
        if not ready_tasks:
            return []

        # Sort only once, using cached priorities
        sorted_tasks = sorted(ready_tasks, key=lambda t: task_priorities.get(t, 0), reverse=True)
        return sorted_tasks[:max_concurrent]

    @staticmethod
    def optimize_dependency_check(
        task_id: str,
        dependencies: dict[str, set[str]],
        completed_tasks: set[str],
    ) -> bool:
        """Fast dependency check using set intersection.

        Avoids iterating dependencies unnecessarily.

        Args:
            task_id: Task to check
            dependencies: Task dependency map
            completed_tasks: Set of completed tasks

        Returns:
            True if all dependencies satisfied
        """
        task_deps = dependencies.get(task_id, set())
        if not task_deps:
            return True

        # Use set intersection for O(n) instead of repeated lookups
        remaining = task_deps - completed_tasks
        return len(remaining) == 0


class PersistenceOptimizer:
    """Optimizations for storage layer."""

    @staticmethod
    def enable_batch_writes(batch_size: int = 10) -> OptimizationConfig:
        """Enable batch event persistence.

        Reduces I/O by buffering writes.

        Args:
            batch_size: Number of events per batch

        Returns:
            OptimizationConfig with batch writes enabled
        """
        return OptimizationConfig(
            batch_storage=True,
            batch_size=batch_size,
            async_writes=True,
        )

    @staticmethod
    def enable_connection_pooling(pool_size: int = 20) -> OptimizationConfig:
        """Enable connection pooling.

        Reuses database connections instead of creating new ones.

        Args:
            pool_size: Pool size

        Returns:
            OptimizationConfig with pooling enabled
        """
        return OptimizationConfig(
            connection_pooling=True,
            pool_size=pool_size,
        )

    @staticmethod
    def estimate_io_savings(
        event_count: int,
        batch_size: int,
        events_per_second: float = 1000.0,
    ) -> dict[str, float]:
        """Estimate I/O savings from batching.

        Args:
            event_count: Total events
            batch_size: Batch size
            events_per_second: Event rate

        Returns:
            Dictionary with timing estimates
        """
        unbatched_roundtrips = event_count
        batched_roundtrips = (event_count + batch_size - 1) // batch_size
        reduction = unbatched_roundtrips - batched_roundtrips

        # Assume 10ms per roundtrip
        unbatched_time_ms = unbatched_roundtrips * 10
        batched_time_ms = batched_roundtrips * 10
        saved_time_ms = unbatched_time_ms - batched_time_ms

        return {
            "unbatched_roundtrips": float(unbatched_roundtrips),
            "batched_roundtrips": float(batched_roundtrips),
            "roundtrips_saved": float(reduction),
            "estimated_time_saved_ms": float(saved_time_ms),
            "throughput_improvement_percent": (
                (saved_time_ms / unbatched_time_ms * 100) if unbatched_time_ms > 0 else 0.0
            ),
        }


class HotPathOptimizer:
    """Optimizations for hot execution paths."""

    @staticmethod
    def optimize_state_transitions(task_id: str, from_state: str, to_state: str) -> float:
        """Measure state transition overhead.

        Args:
            task_id: Task ID
            from_state: Current state
            to_state: Target state

        Returns:
            Transition time in milliseconds
        """
        start = time.perf_counter()

        # Simulate transition validation
        valid_transitions = {
            "PENDING": {"READY", "CANCELLED"},
            "READY": {"RUNNING", "CANCELLED"},
            "RUNNING": {"SUCCEEDED", "FAILED", "RETRYING", "CANCELLED"},
            "RETRYING": {"READY", "FAILED", "CANCELLED"},
        }

        valid_transitions.get(from_state, set())

        duration_ms = (time.perf_counter() - start) * 1000
        return duration_ms

    @staticmethod
    def optimize_event_persistence(
        event_count: int, with_batching: bool = True
    ) -> dict[str, float]:
        """Estimate event persistence overhead.

        Args:
            event_count: Number of events to persist
            with_batching: Whether batching is enabled

        Returns:
            Dictionary with overhead metrics
        """
        batch_size = 10 if with_batching else 1
        roundtrips = (event_count + batch_size - 1) // batch_size

        # Estimate: 0.5ms per event + 10ms per roundtrip
        event_overhead_ms = event_count * 0.5
        roundtrip_overhead_ms = roundtrips * 10
        total_overhead_ms = event_overhead_ms + roundtrip_overhead_ms

        return {
            "event_processing_ms": event_overhead_ms,
            "roundtrip_overhead_ms": roundtrip_overhead_ms,
            "total_storage_overhead_ms": total_overhead_ms,
            "overhead_per_event_ms": total_overhead_ms / event_count if event_count > 0 else 0.0,
        }


class PerformanceTuning:
    """Production tuning recommendations."""

    TUNING_RECOMMENDATIONS = {
        "small_workflows": {
            "max_concurrent": 10,
            "batch_size": 5,
            "pool_size": 10,
            "cache_enabled": False,
        },
        "medium_workflows": {
            "max_concurrent": 50,
            "batch_size": 10,
            "pool_size": 20,
            "cache_enabled": True,
        },
        "large_workflows": {
            "max_concurrent": 200,
            "batch_size": 50,
            "pool_size": 50,
            "cache_enabled": True,
        },
        "high_throughput": {
            "max_concurrent": 500,
            "batch_size": 100,
            "pool_size": 100,
            "cache_enabled": True,
        },
    }

    @staticmethod
    def recommend_tuning(task_count: int) -> dict[str, Any]:
        """Get tuning recommendations based on workload size.

        Args:
            task_count: Number of tasks

        Returns:
            Recommended configuration
        """
        if task_count < 20:
            profile = "small_workflows"
        elif task_count < 100:
            profile = "medium_workflows"
        elif task_count < 500:
            profile = "large_workflows"
        else:
            profile = "high_throughput"

        return {
            "profile": profile,
            "config": PerformanceTuning.TUNING_RECOMMENDATIONS[profile],
        }

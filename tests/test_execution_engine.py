"""Tests for the asynchronous execution engine."""

import asyncio
import pytest

from helixops.domain.models import Workflow, TaskNode, TaskState
from helixops.execution.executor import ExecutionEngine
from helixops.execution.models import (
    ExecutionEventType,
    TaskSimulationConfig,
)


class TestExecutionEngine:
    """Tests for execution engine functionality."""

    @pytest.mark.asyncio
    async def test_single_task_execution(self) -> None:
        """Test execution of a single task."""
        workflow = Workflow(name="SingleTask")
        workflow.add_task(TaskNode(task_id="task1", name="Task 1"))

        engine = ExecutionEngine(workflow)
        config = {"task1": TaskSimulationConfig(task_id="task1", duration_ms=50)}

        result = await engine.execute("run-1", config)

        assert result.succeeded
        assert len(result.task_results) == 1
        assert result.task_results["task1"].succeeded
        assert result.total_duration_ms > 50

    @pytest.mark.asyncio
    async def test_linear_task_execution(self) -> None:
        """Test execution of linearly dependent tasks."""
        workflow = Workflow(name="Linear")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["b"]))

        engine = ExecutionEngine(workflow)
        configs = {
            "a": TaskSimulationConfig(task_id="a", duration_ms=10),
            "b": TaskSimulationConfig(task_id="b", duration_ms=10),
            "c": TaskSimulationConfig(task_id="c", duration_ms=10),
        }

        result = await engine.execute("run-1", configs)

        assert result.succeeded
        assert all(r.succeeded for r in result.task_results.values())
        assert result.total_duration_ms > 30

    @pytest.mark.asyncio
    async def test_fan_out_concurrency(self) -> None:
        """Test that fan-out tasks execute concurrently."""
        workflow = Workflow(name="FanOut")
        workflow.add_task(TaskNode(task_id="root", name="Root"))
        for i in range(3):
            workflow.add_task(
                TaskNode(task_id=f"task{i}", name=f"Task{i}", depends_on=["root"])
            )

        engine = ExecutionEngine(workflow, max_workers=4)
        configs = {
            "root": TaskSimulationConfig(task_id="root", duration_ms=10),
            "task0": TaskSimulationConfig(task_id="task0", duration_ms=50),
            "task1": TaskSimulationConfig(task_id="task1", duration_ms=50),
            "task2": TaskSimulationConfig(task_id="task2", duration_ms=50),
        }

        result = await engine.execute("run-1", configs)

        assert result.succeeded
        # If executed sequentially, would take ~200ms, but concurrent should be ~60ms
        assert result.total_duration_ms < 150

    @pytest.mark.asyncio
    async def test_task_failure(self) -> None:
        """Test handling of task failures."""
        workflow = Workflow(name="WithFailure")
        workflow.add_task(TaskNode(task_id="task1", name="Task 1"))

        engine = ExecutionEngine(workflow, seed=42)
        configs = {
            "task1": TaskSimulationConfig(
                task_id="task1",
                duration_ms=50,
                fail_probability=1.0,
                fail_message="Intentional failure",
            )
        }

        result = await engine.execute("run-1", configs)

        assert not result.succeeded
        assert not result.task_results["task1"].succeeded
        assert "Intentional failure" in result.task_results["task1"].error_message

    @pytest.mark.asyncio
    async def test_skip_task(self) -> None:
        """Test skipping tasks."""
        workflow = Workflow(name="WithSkip")
        workflow.add_task(TaskNode(task_id="task1", name="Task 1"))

        engine = ExecutionEngine(workflow)
        configs = {
            "task1": TaskSimulationConfig(
                task_id="task1", duration_ms=100, should_skip=True
            )
        }

        result = await engine.execute("run-1", configs)

        assert result.succeeded
        assert result.task_results["task1"].was_skipped
        assert result.total_duration_ms < 50

    @pytest.mark.asyncio
    async def test_event_emission(self) -> None:
        """Test that events are properly emitted."""
        workflow = Workflow(name="EventTest")
        workflow.add_task(TaskNode(task_id="task1", name="Task 1"))

        engine = ExecutionEngine(workflow)
        configs = {"task1": TaskSimulationConfig(task_id="task1", duration_ms=10)}

        result = await engine.execute("run-1", configs)

        assert len(result.events) > 0
        assert result.events[0].event_type == ExecutionEventType.RUN_STARTED

        event_types = {e.event_type for e in result.events}
        assert ExecutionEventType.TASK_READY in event_types
        assert ExecutionEventType.TASK_RUNNING in event_types
        assert ExecutionEventType.TASK_SUCCEEDED in event_types
        assert result.events[-1].event_type == ExecutionEventType.RUN_COMPLETED

    @pytest.mark.asyncio
    async def test_concurrency_limit(self) -> None:
        """Test that concurrency is bounded."""
        workflow = Workflow(name="ConcurrencyTest")
        workflow.add_task(TaskNode(task_id="root", name="Root"))
        for i in range(10):
            workflow.add_task(
                TaskNode(task_id=f"task{i}", name=f"Task{i}", depends_on=["root"])
            )

        # Limit to 2 concurrent workers
        engine = ExecutionEngine(workflow, max_workers=2)
        configs = {
            "root": TaskSimulationConfig(task_id="root", duration_ms=10),
        }
        for i in range(10):
            configs[f"task{i}"] = TaskSimulationConfig(
                task_id=f"task{i}", duration_ms=50
            )

        result = await engine.execute("run-1", configs)

        assert result.succeeded
        # With 2 workers and 10 tasks of 50ms each, should take ~250ms
        assert result.total_duration_ms > 200

    @pytest.mark.asyncio
    async def test_diamond_dependency(self) -> None:
        """Test diamond dependency pattern."""
        workflow = Workflow(name="Diamond")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="d", name="D", depends_on=["b", "c"]))

        engine = ExecutionEngine(workflow)
        configs = {
            "a": TaskSimulationConfig(task_id="a", duration_ms=10),
            "b": TaskSimulationConfig(task_id="b", duration_ms=20),
            "c": TaskSimulationConfig(task_id="c", duration_ms=20),
            "d": TaskSimulationConfig(task_id="d", duration_ms=10),
        }

        result = await engine.execute("run-1", configs)

        assert result.succeeded
        # a (10) + max(b, c) (20) + d (10) = ~40ms
        assert result.total_duration_ms > 35

    @pytest.mark.asyncio
    async def test_task_output_payload(self) -> None:
        """Test that task output payload is preserved."""
        workflow = Workflow(name="WithOutput")
        workflow.add_task(TaskNode(task_id="task1", name="Task 1"))

        engine = ExecutionEngine(workflow)
        payload = {"key": "value", "count": 42}
        configs = {
            "task1": TaskSimulationConfig(
                task_id="task1",
                duration_ms=10,
                output_payload=payload,
            )
        }

        result = await engine.execute("run-1", configs)

        assert result.task_results["task1"].output_payload == payload

    @pytest.mark.asyncio
    async def test_deterministic_seed(self) -> None:
        """Test that execution is deterministic with seed."""
        workflow = Workflow(name="Deterministic")
        workflow.add_task(TaskNode(task_id="task1", name="Task 1"))

        # Run with seed
        engine1 = ExecutionEngine(workflow, seed=123)
        configs = {
            "task1": TaskSimulationConfig(
                task_id="task1",
                duration_ms=50,
                fail_probability=0.5,
            )
        }

        result1 = await engine1.execute("run-1", configs)

        # Run again with same seed
        engine2 = ExecutionEngine(workflow, seed=123)
        result2 = await engine2.execute("run-2", configs)

        # Both should have same outcome
        assert result1.succeeded == result2.succeeded
        assert (
            result1.task_results["task1"].succeeded
            == result2.task_results["task1"].succeeded
        )

    @pytest.mark.asyncio
    async def test_event_timestamps_ordered(self) -> None:
        """Test that event timestamps are in order."""
        workflow = Workflow(name="OrderedEvents")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))

        engine = ExecutionEngine(workflow)
        configs = {
            "a": TaskSimulationConfig(task_id="a", duration_ms=20),
            "b": TaskSimulationConfig(task_id="b", duration_ms=20),
        }

        result = await engine.execute("run-1", configs)

        for i in range(len(result.events) - 1):
            assert result.events[i].timestamp <= result.events[i + 1].timestamp

    @pytest.mark.asyncio
    async def test_failed_tasks_tracking(self) -> None:
        """Test tracking of failed tasks."""
        workflow = Workflow(name="MultipleFailures")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B"))
        workflow.add_task(TaskNode(task_id="c", name="C"))

        engine = ExecutionEngine(workflow, seed=42)
        configs = {
            "a": TaskSimulationConfig(task_id="a", duration_ms=10, fail_probability=1.0),
            "b": TaskSimulationConfig(task_id="b", duration_ms=10),
            "c": TaskSimulationConfig(task_id="c", duration_ms=10, fail_probability=1.0),
        }

        result = await engine.execute("run-1", configs)

        failed = result.failed_tasks()
        assert "a" in failed
        assert "c" in failed
        assert "b" not in failed

    @pytest.mark.asyncio
    async def test_successful_and_skipped_tasks(self) -> None:
        """Test tracking of successful and skipped tasks."""
        workflow = Workflow(name="MixedOutcomes")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B"))
        workflow.add_task(TaskNode(task_id="c", name="C"))

        engine = ExecutionEngine(workflow)
        configs = {
            "a": TaskSimulationConfig(task_id="a", duration_ms=10),
            "b": TaskSimulationConfig(task_id="b", duration_ms=10, should_skip=True),
            "c": TaskSimulationConfig(task_id="c", duration_ms=10),
        }

        result = await engine.execute("run-1", configs)

        successful = result.successful_tasks()
        skipped = result.skipped_tasks()

        assert "a" in successful
        assert "c" in successful
        assert "b" in skipped
        assert len(result.failed_tasks()) == 0

    @pytest.mark.asyncio
    async def test_complex_workflow(self) -> None:
        """Test complex workflow with multiple waves."""
        workflow = Workflow(name="Complex")
        workflow.add_task(TaskNode(task_id="start", name="Start"))

        # Wave 1: parallel
        for i in range(3):
            workflow.add_task(
                TaskNode(task_id=f"level1_{i}", name=f"L1_{i}", depends_on=["start"])
            )

        # Wave 2: converge
        workflow.add_task(
            TaskNode(
                task_id="merge",
                name="Merge",
                depends_on=[f"level1_{i}" for i in range(3)],
            )
        )

        # Wave 3: parallel again
        for i in range(2):
            workflow.add_task(
                TaskNode(
                    task_id=f"level2_{i}",
                    name=f"L2_{i}",
                    depends_on=["merge"],
                )
            )

        engine = ExecutionEngine(workflow)
        configs = {
            "start": TaskSimulationConfig(task_id="start", duration_ms=10),
            "merge": TaskSimulationConfig(task_id="merge", duration_ms=10),
        }
        for i in range(3):
            configs[f"level1_{i}"] = TaskSimulationConfig(
                task_id=f"level1_{i}", duration_ms=30
            )
        for i in range(2):
            configs[f"level2_{i}"] = TaskSimulationConfig(
                task_id=f"level2_{i}", duration_ms=20
            )

        result = await engine.execute("run-1", configs)

        assert result.succeeded
        assert len(result.task_results) == 7

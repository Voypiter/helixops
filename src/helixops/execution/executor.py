"""Asynchronous task execution engine with bounded concurrency."""

import asyncio
import random
from datetime import datetime
from typing import Dict, List, Optional, Set

from helixops.domain.models import Workflow, TaskState
from helixops.planning.dag_engine import DAGPlanningEngine
from helixops.planning.models import ExecutionPlan
from helixops.execution.models import (
    ExecutionEvent,
    ExecutionEventType,
    TaskSimulationConfig,
    TaskExecutionResult,
    RunExecutionResult,
)


class ExecutionEngine:
    """Executes workflows asynchronously with bounded concurrency."""

    def __init__(
        self,
        workflow: Workflow,
        max_workers: int = 4,
        seed: Optional[int] = None,
    ):
        self.workflow = workflow
        self.plan = self._create_plan()
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.seed = seed
        if seed is not None:
            random.seed(seed)

    def _create_plan(self) -> ExecutionPlan:
        """Create execution plan from workflow."""
        engine = DAGPlanningEngine(self.workflow)
        return engine.plan()

    async def execute(
        self,
        run_id: str,
        task_configs: Dict[str, TaskSimulationConfig],
        timeout_seconds: Optional[float] = None,
    ) -> RunExecutionResult:
        """Execute workflow and return complete result."""
        start_time = datetime.utcnow()
        events: List[ExecutionEvent] = []
        task_results: Dict[str, TaskExecutionResult] = {}
        task_states: Dict[str, TaskState] = {
            task_id: TaskState.PENDING for task_id in self.plan.task_ordering
        }
        task_attempts: Dict[str, int] = {}

        # Emit run started event
        events.append(
            ExecutionEvent(
                event_type=ExecutionEventType.RUN_STARTED,
                run_id=run_id,
                timestamp=start_time,
            )
        )

        try:
            # Execute all waves
            for wave in self.plan.waves:
                # Prepare tasks: mark ready
                for task_id in wave.task_ids:
                    task_states[task_id] = TaskState.READY
                    events.append(
                        ExecutionEvent(
                            event_type=ExecutionEventType.TASK_READY,
                            run_id=run_id,
                            task_id=task_id,
                            timestamp=datetime.utcnow(),
                        )
                    )

                # Execute wave concurrently
                tasks = [
                    self._execute_task(
                        run_id,
                        task_id,
                        task_configs.get(task_id),
                        task_states,
                        task_attempts,
                        events,
                    )
                    for task_id in wave.task_ids
                ]

                try:
                    wave_results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=timeout_seconds,
                    )

                    for task_id, result in zip(wave.task_ids, wave_results):
                        if isinstance(result, Exception):
                            task_results[task_id] = TaskExecutionResult(
                                task_id=task_id,
                                attempt_id="",
                                succeeded=False,
                                duration_ms=0,
                                error_message=str(result),
                            )
                        else:
                            task_results[task_id] = result

                except asyncio.TimeoutError:
                    # Mark tasks as timed out
                    for task_id in wave.task_ids:
                        task_states[task_id] = TaskState.TIMED_OUT
                        events.append(
                            ExecutionEvent(
                                event_type=ExecutionEventType.TASK_TIMED_OUT,
                                run_id=run_id,
                                task_id=task_id,
                                timestamp=datetime.utcnow(),
                            )
                        )
                        if task_id not in task_results:
                            task_results[task_id] = TaskExecutionResult(
                                task_id=task_id,
                                attempt_id="",
                                succeeded=False,
                                duration_ms=0,
                                error_message="Task execution timed out",
                                timed_out=True,
                            )
                    raise

            # Calculate total duration
            end_time = datetime.utcnow()
            total_duration_ms = (end_time - start_time).total_seconds() * 1000

            # Determine overall success
            failed_tasks = [
                task_id for task_id, result in task_results.items()
                if not result.succeeded and not result.was_skipped
            ]
            succeeded = len(failed_tasks) == 0

            # Emit run completed event
            events.append(
                ExecutionEvent(
                    event_type=(
                        ExecutionEventType.RUN_COMPLETED
                        if succeeded
                        else ExecutionEventType.RUN_FAILED
                    ),
                    run_id=run_id,
                    timestamp=end_time,
                    metadata={"failed_count": len(failed_tasks)},
                )
            )

            return RunExecutionResult(
                run_id=run_id,
                workflow_id=self.workflow.workflow_id,
                succeeded=succeeded,
                total_duration_ms=total_duration_ms,
                task_results=task_results,
                events=events,
            )

        except Exception as e:
            end_time = datetime.utcnow()
            total_duration_ms = (end_time - start_time).total_seconds() * 1000

            events.append(
                ExecutionEvent(
                    event_type=ExecutionEventType.RUN_FAILED,
                    run_id=run_id,
                    timestamp=end_time,
                    error_message=str(e),
                )
            )

            return RunExecutionResult(
                run_id=run_id,
                workflow_id=self.workflow.workflow_id,
                succeeded=False,
                total_duration_ms=total_duration_ms,
                task_results=task_results,
                events=events,
                error_message=str(e),
            )

    async def _execute_task(
        self,
        run_id: str,
        task_id: str,
        config: Optional[TaskSimulationConfig],
        task_states: Dict[str, TaskState],
        task_attempts: Dict[str, int],
        events: List[ExecutionEvent],
    ) -> TaskExecutionResult:
        """Execute a single task with simulated behavior."""
        async with self.semaphore:
            attempt_id = f"{task_id}-attempt-{task_attempts.get(task_id, 0) + 1}"
            task_attempts[task_id] = task_attempts.get(task_id, 0) + 1

            # Default config if not provided
            if config is None:
                config = TaskSimulationConfig(task_id=task_id)

            # Check if task should be skipped
            if config.should_skip:
                task_states[task_id] = TaskState.SKIPPED
                events.append(
                    ExecutionEvent(
                        event_type=ExecutionEventType.TASK_SKIPPED,
                        run_id=run_id,
                        task_id=task_id,
                        attempt_id=attempt_id,
                        timestamp=datetime.utcnow(),
                    )
                )
                return TaskExecutionResult(
                    task_id=task_id,
                    attempt_id=attempt_id,
                    succeeded=True,
                    duration_ms=0,
                    was_skipped=True,
                )

            try:
                # Mark running
                task_states[task_id] = TaskState.RUNNING
                start_time = datetime.utcnow()
                events.append(
                    ExecutionEvent(
                        event_type=ExecutionEventType.TASK_RUNNING,
                        run_id=run_id,
                        task_id=task_id,
                        attempt_id=attempt_id,
                        timestamp=start_time,
                    )
                )

                # Simulate task duration
                duration_seconds = config.duration_ms / 1000.0

                # Check for simulated failure
                should_fail = random.random() < config.fail_probability

                if should_fail:
                    # Simulate failure
                    await asyncio.sleep(duration_seconds * 0.5)
                    task_states[task_id] = TaskState.FAILED
                    end_time = datetime.utcnow()
                    duration_ms = (end_time - start_time).total_seconds() * 1000

                    events.append(
                        ExecutionEvent(
                            event_type=ExecutionEventType.TASK_FAILED,
                            run_id=run_id,
                            task_id=task_id,
                            attempt_id=attempt_id,
                            timestamp=end_time,
                            duration_ms=duration_ms,
                            error_message=config.fail_message or "Simulated failure",
                        )
                    )

                    return TaskExecutionResult(
                        task_id=task_id,
                        attempt_id=attempt_id,
                        succeeded=False,
                        duration_ms=duration_ms,
                        error_message=config.fail_message or "Simulated failure",
                    )

                # Normal execution
                await asyncio.sleep(duration_seconds)
                task_states[task_id] = TaskState.SUCCEEDED
                end_time = datetime.utcnow()
                duration_ms = (end_time - start_time).total_seconds() * 1000

                events.append(
                    ExecutionEvent(
                        event_type=ExecutionEventType.TASK_SUCCEEDED,
                        run_id=run_id,
                        task_id=task_id,
                        attempt_id=attempt_id,
                        timestamp=end_time,
                        duration_ms=duration_ms,
                        metadata={"output": config.output_payload},
                    )
                )

                return TaskExecutionResult(
                    task_id=task_id,
                    attempt_id=attempt_id,
                    succeeded=True,
                    duration_ms=duration_ms,
                    output_payload=config.output_payload,
                )

            except asyncio.CancelledError:
                task_states[task_id] = TaskState.CANCELLED
                events.append(
                    ExecutionEvent(
                        event_type=ExecutionEventType.TASK_CANCELLED,
                        run_id=run_id,
                        task_id=task_id,
                        attempt_id=attempt_id,
                        timestamp=datetime.utcnow(),
                    )
                )
                raise

            except Exception as e:
                task_states[task_id] = TaskState.FAILED
                end_time = datetime.utcnow()
                duration_ms = (end_time - start_time).total_seconds() * 1000

                events.append(
                    ExecutionEvent(
                        event_type=ExecutionEventType.TASK_FAILED,
                        run_id=run_id,
                        task_id=task_id,
                        attempt_id=attempt_id,
                        timestamp=end_time,
                        duration_ms=duration_ms,
                        error_message=str(e),
                    )
                )

                return TaskExecutionResult(
                    task_id=task_id,
                    attempt_id=attempt_id,
                    succeeded=False,
                    duration_ms=duration_ms,
                    error_message=str(e),
                )

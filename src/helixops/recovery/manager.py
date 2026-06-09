"""Crash recovery manager for resuming interrupted executions."""

from sqlalchemy.orm import Session

from helixops.recovery.models import (
    RecoveryAction,
    RecoveryResult,
    RecoveryState,
    RunRecoveryState,
    TaskRecoveryDecision,
)
from helixops.storage.models import ExecutionEventModel, TaskAttemptModel
from helixops.storage.repository import (
    ExecutionEventRepository,
    ExecutionRunRepository,
    TaskAttemptRepository,
)


class CrashRecoveryManager:
    """Manages safe recovery from interrupted workflow execution."""

    def __init__(self, session: Session):
        """Initialize recovery manager.

        Args:
            session: SQLAlchemy session for database access
        """
        self.session = session
        self.runs = ExecutionRunRepository(session)
        self.attempts = TaskAttemptRepository(session)
        self.events = ExecutionEventRepository(session)

    def inspect_run_state(self, run_id: str) -> RunRecoveryState:
        """Inspect and classify the state of a run.

        Args:
            run_id: Run identifier to inspect

        Returns:
            RunRecoveryState with classification of all tasks
        """
        run = self.runs.get(run_id)
        if run is None:
            raise ValueError(f"Run {run_id} not found")

        events = self.events.get_by_run(run_id)
        attempts = self.attempts.get_by_run(run_id)

        # Classify run state
        has_run_start = any(e.event_type in {"RUN_STARTED", "RUN_RUNNING"} for e in events)
        has_run_end = any(
            e.event_type in {"RUN_SUCCEEDED", "RUN_FAILED", "RUN_CANCELLED"} for e in events
        )

        # Classify each task
        incomplete_tasks: list[str] = []
        in_progress_tasks: list[str] = []
        completed_tasks: list[str] = []
        failed_tasks: list[str] = []
        unknown_tasks: list[str] = []

        task_ids = {attempt.task_id for attempt in attempts}

        for task_id in task_ids:
            recovery_state = self._classify_task_state(task_id, run_id, attempts, events)  # type: ignore[arg-type]

            if recovery_state == RecoveryState.COMPLETED:
                completed_tasks.append(task_id)  # type: ignore[arg-type]
            elif recovery_state == RecoveryState.FAILED:
                failed_tasks.append(task_id)  # type: ignore[arg-type]
            elif recovery_state == RecoveryState.SAFE_TO_RESUME:
                in_progress_tasks.append(task_id)  # type: ignore[arg-type]
            elif recovery_state == RecoveryState.UNSAFE:
                incomplete_tasks.append(task_id)  # type: ignore[arg-type]
            else:  # UNKNOWN
                unknown_tasks.append(task_id)  # type: ignore[arg-type]

        return RunRecoveryState(
            run_id=run_id,
            workflow_id=run.workflow_id,  # type: ignore[arg-type]
            is_complete=has_run_end,
            incomplete_tasks=incomplete_tasks,
            in_progress_tasks=in_progress_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            unknown_tasks=unknown_tasks,
            total_event_count=len(events),
            has_run_start=has_run_start,
            has_run_end=has_run_end,
            last_event_timestamp=events[-1].timestamp if events else None,  # type: ignore[arg-type]
        )

    def _classify_task_state(
        self,
        task_id: str,
        run_id: str,
        all_attempts: list[TaskAttemptModel],
        all_events: list[ExecutionEventModel],
    ) -> RecoveryState:
        """Classify recovery state for a single task.

        Args:
            task_id: Task to classify
            run_id: Run identifier
            all_attempts: All attempts in the run
            all_events: All events in the run

        Returns:
            RecoveryState classification
        """
        # Get attempts for this task
        task_attempts = [a for a in all_attempts if a.task_id == task_id]
        if not task_attempts:
            return RecoveryState.UNKNOWN

        max(task_attempts, key=lambda a: a.attempt_number)
        task_events = [e for e in all_events if e.task_id == task_id]

        if not task_events:
            # No events at all - unsafe state
            return RecoveryState.UNSAFE

        # Get the last event
        last_event = max(task_events, key=lambda e: e.timestamp)

        # Completed if last event is success
        if last_event.event_type == "TASK_SUCCEEDED":
            return RecoveryState.COMPLETED

        # Failed if last event is failure
        if last_event.event_type == "TASK_FAILED":
            return RecoveryState.FAILED

        # In progress if last event is running
        if last_event.event_type == "TASK_RUNNING":
            # Check if we have event history completeness
            has_start = any(e.event_type == "TASK_PENDING" for e in task_events)
            if has_start:
                return RecoveryState.SAFE_TO_RESUME
            return RecoveryState.UNSAFE

        # Retrying state
        if last_event.event_type == "TASK_RETRYING":
            return RecoveryState.SAFE_TO_RESUME

        # Unknown or incomplete events
        return RecoveryState.UNKNOWN

    def recover_run(self, run_id: str) -> RecoveryResult:
        """Recover an interrupted run.

        Args:
            run_id: Run to recover

        Returns:
            RecoveryResult with all decisions and statistics
        """
        try:
            recovery_state = self.inspect_run_state(run_id)
        except ValueError as e:
            return RecoveryResult(
                run_id=run_id,
                recovered=False,
                recovery_errors=[str(e)],
            )

        # If run is complete, no recovery needed
        if recovery_state.is_complete:
            return RecoveryResult(
                run_id=run_id,
                recovered=True,
                preserved_tasks=len(recovery_state.completed_tasks),
                failed_tasks=len(recovery_state.failed_tasks),
            )

        decisions: list[TaskRecoveryDecision] = []

        # Preserve all completed tasks
        for task_id in recovery_state.completed_tasks:
            decisions.append(
                TaskRecoveryDecision(
                    task_id=task_id,
                    recovery_state=RecoveryState.COMPLETED,
                    action=RecoveryAction.PRESERVE,
                    reason="Task completed successfully",
                    is_safe=True,
                )
            )

        # Preserve all failed tasks
        for task_id in recovery_state.failed_tasks:
            decisions.append(
                TaskRecoveryDecision(
                    task_id=task_id,
                    recovery_state=RecoveryState.FAILED,
                    action=RecoveryAction.PRESERVE,
                    reason="Task already failed",
                    is_safe=True,
                )
            )

        # Requeue safe in-progress tasks
        for task_id in recovery_state.in_progress_tasks:
            decisions.append(
                TaskRecoveryDecision(
                    task_id=task_id,
                    recovery_state=RecoveryState.SAFE_TO_RESUME,
                    action=RecoveryAction.REQUEUE,
                    reason="Task execution interrupted but in valid state",
                    is_safe=True,
                )
            )

        # Mark incomplete tasks as failed (conservative approach)
        for task_id in recovery_state.incomplete_tasks:
            decisions.append(
                TaskRecoveryDecision(
                    task_id=task_id,
                    recovery_state=RecoveryState.UNSAFE,
                    action=RecoveryAction.MARK_FAILED,
                    reason="Task in ambiguous/unsafe state, not resuming",
                    is_safe=False,
                )
            )

        # Mark unknown tasks as failed (conservative)
        for task_id in recovery_state.unknown_tasks:
            decisions.append(
                TaskRecoveryDecision(
                    task_id=task_id,
                    recovery_state=RecoveryState.UNKNOWN,
                    action=RecoveryAction.MARK_FAILED,
                    reason="Task state unknown after crash",
                    is_safe=False,
                )
            )

        # Count results
        preserved = len(recovery_state.completed_tasks) + len(recovery_state.failed_tasks)
        requeued = len(recovery_state.in_progress_tasks)
        failed = len(recovery_state.incomplete_tasks) + len(recovery_state.unknown_tasks)

        return RecoveryResult(
            run_id=run_id,
            recovered=True,
            decisions=decisions,
            preserved_tasks=preserved,
            requeued_tasks=requeued,
            failed_tasks=failed,
            total_decisions=len(decisions),
        )

    def can_safely_resume_task(self, task_id: str, run_id: str) -> bool:
        """Determine if a task can be safely resumed.

        Args:
            task_id: Task identifier
            run_id: Run identifier

        Returns:
            True if task can be safely resumed
        """
        try:
            recovery_state = self.inspect_run_state(run_id)
            return task_id in recovery_state.in_progress_tasks
        except ValueError:
            return False

    def get_completed_tasks(self, run_id: str) -> set[str]:
        """Get all completed tasks in a run.

        Args:
            run_id: Run identifier

        Returns:
            Set of completed task IDs
        """
        recovery_state = self.inspect_run_state(run_id)
        return set(recovery_state.completed_tasks)

    def get_tasks_to_requeue(self, run_id: str) -> list[str]:
        """Get tasks that should be requeued.

        Args:
            run_id: Run identifier

        Returns:
            List of task IDs to requeue
        """
        recovery_state = self.inspect_run_state(run_id)
        return recovery_state.in_progress_tasks

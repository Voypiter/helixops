"""Repository abstractions for data persistence."""

from typing import List, Optional
from sqlalchemy.orm import Session

from helixops.storage.models import (
    WorkflowModel,
    ExecutionRunModel,
    TaskAttemptModel,
    ExecutionEventModel,
)
from helixops.execution.models import ExecutionEvent, TaskExecutionResult, RunExecutionResult


class WorkflowRepository:
    """Repository for workflow persistence."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, workflow_id: str, name: str, definition: dict) -> WorkflowModel:
        """Save a workflow definition."""
        workflow = WorkflowModel(
            workflow_id=workflow_id,
            name=name,
            definition=definition,
        )
        self.session.add(workflow)
        self.session.flush()
        return workflow

    def get(self, workflow_id: str) -> Optional[WorkflowModel]:
        """Get a workflow by ID."""
        return self.session.query(WorkflowModel).filter_by(workflow_id=workflow_id).first()

    def list_all(self) -> List[WorkflowModel]:
        """Get all workflows."""
        return self.session.query(WorkflowModel).all()


class ExecutionRunRepository:
    """Repository for execution run persistence."""

    def __init__(self, session: Session):
        self.session = session

    def save(
        self,
        run_id: str,
        workflow_id: str,
        state: str,
    ) -> ExecutionRunModel:
        """Create a new execution run."""
        run = ExecutionRunModel(
            run_id=run_id,
            workflow_id=workflow_id,
            state=state,
        )
        self.session.add(run)
        self.session.flush()
        return run

    def update(self, run: ExecutionRunModel) -> None:
        """Update an execution run."""
        self.session.merge(run)
        self.session.flush()

    def get(self, run_id: str) -> Optional[ExecutionRunModel]:
        """Get a run by ID."""
        return self.session.query(ExecutionRunModel).filter_by(run_id=run_id).first()

    def get_by_workflow(self, workflow_id: str) -> List[ExecutionRunModel]:
        """Get all runs for a workflow."""
        return (
            self.session.query(ExecutionRunModel)
            .filter_by(workflow_id=workflow_id)
            .all()
        )


class TaskAttemptRepository:
    """Repository for task attempt persistence."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, attempt: TaskAttemptModel) -> TaskAttemptModel:
        """Save a task attempt."""
        self.session.add(attempt)
        self.session.flush()
        return attempt

    def update(self, attempt: TaskAttemptModel) -> None:
        """Update a task attempt."""
        self.session.merge(attempt)
        self.session.flush()

    def get(self, attempt_id: str) -> Optional[TaskAttemptModel]:
        """Get an attempt by ID."""
        return (
            self.session.query(TaskAttemptModel)
            .filter_by(attempt_id=attempt_id)
            .first()
        )

    def get_by_run(self, run_id: str) -> List[TaskAttemptModel]:
        """Get all attempts in a run."""
        return (
            self.session.query(TaskAttemptModel)
            .filter_by(run_id=run_id)
            .all()
        )

    def get_by_task(self, run_id: str, task_id: str) -> List[TaskAttemptModel]:
        """Get all attempts for a task in a run."""
        return (
            self.session.query(TaskAttemptModel)
            .filter_by(run_id=run_id, task_id=task_id)
            .all()
        )


class ExecutionEventRepository:
    """Repository for execution event persistence."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, event: ExecutionEventModel) -> ExecutionEventModel:
        """Save an execution event."""
        self.session.add(event)
        self.session.flush()
        return event

    def get(self, event_id: str) -> Optional[ExecutionEventModel]:
        """Get an event by ID."""
        return (
            self.session.query(ExecutionEventModel)
            .filter_by(event_id=event_id)
            .first()
        )

    def get_by_run(self, run_id: str) -> List[ExecutionEventModel]:
        """Get all events for a run."""
        return (
            self.session.query(ExecutionEventModel)
            .filter_by(run_id=run_id)
            .order_by(ExecutionEventModel.timestamp)
            .all()
        )

    def get_by_task(self, attempt_id: str) -> List[ExecutionEventModel]:
        """Get all events for a task attempt."""
        return (
            self.session.query(ExecutionEventModel)
            .filter_by(attempt_id=attempt_id)
            .order_by(ExecutionEventModel.timestamp)
            .all()
        )


class PersistenceService:
    """Service for persisting execution results."""

    def __init__(self, session: Session):
        self.session = session
        self.workflows = WorkflowRepository(session)
        self.runs = ExecutionRunRepository(session)
        self.attempts = TaskAttemptRepository(session)
        self.events = ExecutionEventRepository(session)

    def persist_run_result(self, result: RunExecutionResult) -> None:
        """Persist a complete run result to the database."""
        # Create or update run
        run = self.runs.get(result.run_id)
        if run is None:
            run = ExecutionRunModel(
                run_id=result.run_id,
                workflow_id=result.workflow_id,
                state="RUNNING",
            )
            self.session.add(run)
        else:
            run = self.session.merge(run)

        # Update run with final state
        run.succeeded = result.succeeded
        run.completed_at = result.events[-1].timestamp if result.events else None
        run.total_duration_ms = result.total_duration_ms
        run.error_message = result.error_message
        run.state = "SUCCEEDED" if result.succeeded else "FAILED"

        # Persist task attempts
        for task_id, task_result in result.task_results.items():
            attempt = TaskAttemptModel(
                attempt_id=task_result.attempt_id,
                run_id=result.run_id,
                task_id=task_id,
                attempt_number=1,
                state="SUCCEEDED" if task_result.succeeded else "FAILED",
                succeeded=task_result.succeeded,
                duration_ms=task_result.duration_ms,
                error_message=task_result.error_message,
                output_payload=task_result.output_payload,
                was_skipped=task_result.was_skipped,
                was_cancelled=task_result.was_cancelled,
                was_timed_out=task_result.timed_out,
            )
            self.session.add(attempt)

        # Persist events
        for event in result.events:
            db_event = ExecutionEventModel(
                event_id=event.event_id,
                run_id=event.run_id,
                attempt_id=event.attempt_id,
                task_id=event.task_id,
                event_type=event.event_type.value,
                timestamp=event.timestamp,
                duration_ms=event.duration_ms,
                error_message=event.error_message,
                metadata_json=event.metadata,
            )
            self.session.add(db_event)

        self.session.commit()

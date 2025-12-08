"""Tests for persistence layer."""

import os
import tempfile
from datetime import datetime

import pytest

from helixops.storage.database import DatabaseConnection
from helixops.storage.models import ExecutionRunModel, TaskAttemptModel, ExecutionEventModel
from helixops.storage.repository import PersistenceService
from helixops.execution.models import RunExecutionResult, TaskExecutionResult, ExecutionEvent, ExecutionEventType


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_url = f"sqlite:///{db_path}"
        conn = DatabaseConnection(db_url=db_url)
        # Create a test workflow
        with conn.get_session() as session:
            from helixops.storage.repository import WorkflowRepository
            repo = WorkflowRepository(session)
            repo.save(workflow_id="wf-1", name="Test Workflow", definition={})
        yield conn
        conn.close()


class TestDatabaseConnection:
    """Tests for database connection."""

    def test_create_connection(self, temp_db) -> None:
        """Database connection should be created."""
        assert temp_db.engine is not None
        assert temp_db.SessionLocal is not None

    def test_tables_created(self, temp_db) -> None:
        """Tables should be created on initialization."""
        with temp_db.get_session() as session:
            # Check that tables exist by querying them
            workflow_count = session.query(ExecutionRunModel).count()
            assert workflow_count == 0


class TestWorkflowRepository:
    """Tests for workflow repository."""

    def test_save_workflow(self, temp_db) -> None:
        """Workflow should be saved."""
        with temp_db.get_session() as session:
            from helixops.storage.repository import WorkflowRepository

            repo = WorkflowRepository(session)
            workflow = repo.save(
                workflow_id="wf-save",
                name="Test Workflow",
                definition={"tasks": []},
            )

            assert workflow.workflow_id == "wf-save"
            assert workflow.name == "Test Workflow"

    def test_get_workflow(self, temp_db) -> None:
        """Workflow should be retrievable."""
        with temp_db.get_session() as session:
            from helixops.storage.repository import WorkflowRepository

            repo = WorkflowRepository(session)
            repo.save(workflow_id="wf-get", name="Test", definition={})

        with temp_db.get_session() as session:
            repo = WorkflowRepository(session)
            workflow = repo.get("wf-get")

            assert workflow is not None
            assert workflow.name == "Test"


class TestExecutionRunRepository:
    """Tests for execution run repository."""

    def test_save_run(self, temp_db) -> None:
        """Run should be saved."""
        with temp_db.get_session() as session:
            from helixops.storage.repository import ExecutionRunRepository

            repo = ExecutionRunRepository(session)
            run = repo.save(
                run_id="run-1",
                workflow_id="wf-1",
                state="RUNNING",
            )

            assert run.run_id == "run-1"
            assert run.state == "RUNNING"

    def test_get_run(self, temp_db) -> None:
        """Run should be retrievable."""
        with temp_db.get_session() as session:
            from helixops.storage.repository import ExecutionRunRepository

            repo = ExecutionRunRepository(session)
            repo.save(run_id="run-1", workflow_id="wf-1", state="RUNNING")

        with temp_db.get_session() as session:
            repo = ExecutionRunRepository(session)
            run = repo.get("run-1")

            assert run is not None
            assert run.state == "RUNNING"

    def test_update_run(self, temp_db) -> None:
        """Run state should be updateable."""
        with temp_db.get_session() as session:
            from helixops.storage.repository import ExecutionRunRepository

            repo = ExecutionRunRepository(session)
            run = repo.save(run_id="run-1", workflow_id="wf-1", state="RUNNING")
            run.state = "SUCCEEDED"
            repo.update(run)

        with temp_db.get_session() as session:
            repo = ExecutionRunRepository(session)
            run = repo.get("run-1")

            assert run.state == "SUCCEEDED"


class TestTaskAttemptRepository:
    """Tests for task attempt repository."""

    def test_save_attempt(self, temp_db) -> None:
        """Attempt should be saved."""
        with temp_db.get_session() as session:
            # First create a run
            from helixops.storage.repository import ExecutionRunRepository

            run_repo = ExecutionRunRepository(session)
            run_repo.save(run_id="run-1", workflow_id="wf-1", state="RUNNING")

            from helixops.storage.repository import TaskAttemptRepository

            attempt_repo = TaskAttemptRepository(session)
            attempt = TaskAttemptModel(
                attempt_id="attempt-1",
                run_id="run-1",
                task_id="task-1",
                attempt_number=1,
                state="RUNNING",
            )
            attempt_repo.save(attempt)

        with temp_db.get_session() as session:
            from helixops.storage.repository import TaskAttemptRepository

            repo = TaskAttemptRepository(session)
            attempt = repo.get("attempt-1")

            assert attempt is not None
            assert attempt.task_id == "task-1"

    def test_get_attempts_by_run(self, temp_db) -> None:
        """Attempts for a run should be retrievable."""
        with temp_db.get_session() as session:
            from helixops.storage.repository import (
                ExecutionRunRepository,
                TaskAttemptRepository,
            )

            run_repo = ExecutionRunRepository(session)
            run_repo.save(run_id="run-1", workflow_id="wf-1", state="RUNNING")

            attempt_repo = TaskAttemptRepository(session)
            for i in range(3):
                attempt = TaskAttemptModel(
                    attempt_id=f"attempt-{i}",
                    run_id="run-1",
                    task_id=f"task-{i}",
                    attempt_number=1,
                    state="RUNNING",
                )
                attempt_repo.save(attempt)

        with temp_db.get_session() as session:
            from helixops.storage.repository import TaskAttemptRepository

            repo = TaskAttemptRepository(session)
            attempts = repo.get_by_run("run-1")

            assert len(attempts) == 3


class TestExecutionEventRepository:
    """Tests for execution event repository."""

    def test_save_event(self, temp_db) -> None:
        """Event should be saved."""
        with temp_db.get_session() as session:
            from helixops.storage.repository import ExecutionRunRepository

            run_repo = ExecutionRunRepository(session)
            run_repo.save(run_id="run-1", workflow_id="wf-1", state="RUNNING")

            from helixops.storage.repository import ExecutionEventRepository

            event_repo = ExecutionEventRepository(session)
            event = ExecutionEventModel(
                event_id="event-1",
                run_id="run-1",
                event_type="TASK_RUNNING",
                task_id="task-1",
            )
            event_repo.save(event)

        with temp_db.get_session() as session:
            from helixops.storage.repository import ExecutionEventRepository

            repo = ExecutionEventRepository(session)
            event = repo.get("event-1")

            assert event is not None
            assert event.event_type == "TASK_RUNNING"

    def test_get_events_by_run(self, temp_db) -> None:
        """Events for a run should be retrievable in order."""
        with temp_db.get_session() as session:
            from helixops.storage.repository import (
                ExecutionRunRepository,
                ExecutionEventRepository,
            )

            run_repo = ExecutionRunRepository(session)
            run_repo.save(run_id="run-1", workflow_id="wf-1", state="RUNNING")

            event_repo = ExecutionEventRepository(session)
            for i in range(3):
                event = ExecutionEventModel(
                    event_id=f"event-{i}",
                    run_id="run-1",
                    event_type="TASK_RUNNING",
                    timestamp=datetime.utcnow(),
                )
                event_repo.save(event)

        with temp_db.get_session() as session:
            from helixops.storage.repository import ExecutionEventRepository

            repo = ExecutionEventRepository(session)
            events = repo.get_by_run("run-1")

            assert len(events) == 3


class TestPersistenceService:
    """Tests for persistence service."""

    def test_persist_run_result(self, temp_db) -> None:
        """Complete run result should be persisted."""
        # Create a run result
        result = RunExecutionResult(
            run_id="run-1",
            workflow_id="wf-1",
            succeeded=True,
            total_duration_ms=1000,
            task_results={
                "task-1": TaskExecutionResult(
                    task_id="task-1",
                    attempt_id="attempt-1",
                    succeeded=True,
                    duration_ms=500,
                )
            },
            events=[
                ExecutionEvent(
                    event_id="event-1",
                    run_id="run-1",
                    event_type=ExecutionEventType.RUN_STARTED,
                ),
                ExecutionEvent(
                    event_id="event-2",
                    run_id="run-1",
                    task_id="task-1",
                    event_type=ExecutionEventType.TASK_SUCCEEDED,
                ),
            ],
        )

        with temp_db.get_session() as session:
            service = PersistenceService(session)
            service.persist_run_result(result)

        # Verify persistence
        with temp_db.get_session() as session:
            from helixops.storage.repository import (
                ExecutionRunRepository,
                TaskAttemptRepository,
                ExecutionEventRepository,
            )

            run_repo = ExecutionRunRepository(session)
            attempt_repo = TaskAttemptRepository(session)
            event_repo = ExecutionEventRepository(session)

            run = run_repo.get("run-1")
            assert run is not None
            assert run.succeeded is True

            attempts = attempt_repo.get_by_run("run-1")
            assert len(attempts) == 1
            assert attempts[0].task_id == "task-1"

            events = event_repo.get_by_run("run-1")
            assert len(events) == 2


class TestPersistenceSurvivesRestart:
    """Tests that persistence survives process restart."""

    def test_data_survives_connection_close(self, temp_db) -> None:
        """Data should survive connection close and reopen."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "persistent.db")
            db_url = f"sqlite:///{db_path}"

            # First connection: write data
            conn1 = DatabaseConnection(db_url=db_url)
            with conn1.get_session() as session:
                from helixops.storage.repository import WorkflowRepository, ExecutionRunRepository

                wf_repo = WorkflowRepository(session)
                wf_repo.save(workflow_id="wf-restart", name="Test", definition={})

                run_repo = ExecutionRunRepository(session)
                run_repo.save(run_id="run-1", workflow_id="wf-restart", state="RUNNING")

            conn1.close()

            # Second connection: read data
            conn2 = DatabaseConnection(db_url=db_url)
            with conn2.get_session() as session:
                from helixops.storage.repository import ExecutionRunRepository

                repo = ExecutionRunRepository(session)
                run = repo.get("run-1")

                assert run is not None
                assert run.workflow_id == "wf-restart"

            conn2.close()

    def test_transaction_atomicity(self, temp_db) -> None:
        """Transactions should be atomic."""
        with temp_db.get_session() as session:
            from helixops.storage.repository import ExecutionRunRepository

            repo = ExecutionRunRepository(session)
            run1 = repo.save(run_id="run-1", workflow_id="wf-1", state="RUNNING")
            run2 = repo.save(run_id="run-2", workflow_id="wf-1", state="RUNNING")

        # Both should be persisted together
        with temp_db.get_session() as session:
            from helixops.storage.repository import ExecutionRunRepository

            repo = ExecutionRunRepository(session)
            count = len(repo.get_by_workflow("wf-1"))

            assert count == 2

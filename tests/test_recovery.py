"""Tests for crash recovery and state reconciliation."""

import os
import tempfile
from datetime import datetime, timedelta

import pytest  # noqa: F401

from helixops.recovery.audit import RecoveryAuditTrail
from helixops.recovery.manager import CrashRecoveryManager
from helixops.recovery.models import RecoveryAction, RecoveryState
from helixops.storage.database import DatabaseConnection
from helixops.storage.models import ExecutionEventModel, TaskAttemptModel
from helixops.storage.repository import (
    ExecutionEventRepository,
    ExecutionRunRepository,
    TaskAttemptRepository,
    WorkflowRepository,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_url = f"sqlite:///{db_path}"
        conn = DatabaseConnection(db_url=db_url)
        # Create test workflow
        with conn.get_session() as session:
            repo = WorkflowRepository(session)
            repo.save(workflow_id="wf-recovery", name="Recovery Test", definition={})
        yield conn
        conn.close()


class TestCrashRecoveryManager:
    """Tests for crash recovery manager."""

    def test_inspect_completed_run(self, temp_db) -> None:
        """Should recognize completed runs."""
        with temp_db.get_session() as session:
            run_repo = ExecutionRunRepository(session)
            run_repo.save(run_id="run-1", workflow_id="wf-recovery", state="SUCCEEDED")

            attempt_repo = TaskAttemptRepository(session)
            attempt = TaskAttemptModel(
                attempt_id="attempt-1",
                run_id="run-1",
                task_id="task-1",
                attempt_number=1,
                state="SUCCEEDED",
                succeeded=True,
            )
            attempt_repo.save(attempt)

            event_repo = ExecutionEventRepository(session)
            base_time = datetime.utcnow()
            for i, event_type in enumerate(
                ["RUN_STARTED", "TASK_PENDING", "TASK_RUNNING", "TASK_SUCCEEDED", "RUN_SUCCEEDED"]
            ):
                event = ExecutionEventModel(
                    event_id=f"event-{event_type}",
                    run_id="run-1",
                    task_id="task-1" if event_type.startswith("TASK") else None,
                    event_type=event_type,
                    timestamp=base_time + timedelta(milliseconds=i),
                )
                event_repo.save(event)

        with temp_db.get_session() as session:
            manager = CrashRecoveryManager(session)
            state = manager.inspect_run_state("run-1")

            assert state.is_complete is True
            assert "task-1" in state.completed_tasks
            assert len(state.incomplete_tasks) == 0

    def test_inspect_interrupted_run(self, temp_db) -> None:
        """Should identify interrupted runs with tasks in progress."""
        with temp_db.get_session() as session:
            run_repo = ExecutionRunRepository(session)
            run_repo.save(run_id="run-1", workflow_id="wf-recovery", state="RUNNING")

            attempt_repo = TaskAttemptRepository(session)
            attempt = TaskAttemptModel(
                attempt_id="attempt-1",
                run_id="run-1",
                task_id="task-1",
                attempt_number=1,
                state="RUNNING",
            )
            attempt_repo.save(attempt)

            event_repo = ExecutionEventRepository(session)
            base_time = datetime.utcnow()
            for i, event_type in enumerate(["RUN_STARTED", "TASK_PENDING", "TASK_RUNNING"]):
                event = ExecutionEventModel(
                    event_id=f"event-{event_type}",
                    run_id="run-1",
                    task_id="task-1" if event_type.startswith("TASK") else None,
                    event_type=event_type,
                    timestamp=base_time + timedelta(milliseconds=i),
                )
                event_repo.save(event)

        with temp_db.get_session() as session:
            manager = CrashRecoveryManager(session)
            state = manager.inspect_run_state("run-1")

            assert state.is_complete is False
            assert "task-1" in state.in_progress_tasks
            assert state.has_run_start is True
            assert state.has_run_end is False

    def test_crash_during_running_task(self, temp_db) -> None:
        """Should handle crash during task execution."""
        with temp_db.get_session() as session:
            run_repo = ExecutionRunRepository(session)
            run_repo.save(run_id="run-1", workflow_id="wf-recovery", state="RUNNING")

            attempt_repo = TaskAttemptRepository(session)
            attempt = TaskAttemptModel(
                attempt_id="attempt-1",
                run_id="run-1",
                task_id="task-1",
                attempt_number=1,
                state="RUNNING",
            )
            attempt_repo.save(attempt)

            event_repo = ExecutionEventRepository(session)
            base_time = datetime.utcnow()
            for i, event_type in enumerate(["RUN_STARTED", "TASK_PENDING", "TASK_RUNNING"]):
                event = ExecutionEventModel(
                    event_id=f"event-{event_type}",
                    run_id="run-1",
                    task_id="task-1" if event_type.startswith("TASK") else None,
                    event_type=event_type,
                    timestamp=base_time + timedelta(milliseconds=i),
                )
                event_repo.save(event)

        with temp_db.get_session() as session:
            manager = CrashRecoveryManager(session)
            result = manager.recover_run("run-1")

            assert result.recovered is True
            assert result.requeued_tasks == 1
            assert len(result.decisions) == 1
            assert result.decisions[0].action == RecoveryAction.REQUEUE

    def test_crash_preserves_completed_work(self, temp_db) -> None:
        """Should preserve completed tasks when recovering."""
        with temp_db.get_session() as session:
            run_repo = ExecutionRunRepository(session)
            run_repo.save(run_id="run-1", workflow_id="wf-recovery", state="RUNNING")

            attempt_repo = TaskAttemptRepository(session)
            for task_num in [1, 2]:
                attempt = TaskAttemptModel(
                    attempt_id=f"attempt-{task_num}",
                    run_id="run-1",
                    task_id=f"task-{task_num}",
                    attempt_number=1,
                    state="SUCCEEDED" if task_num == 1 else "RUNNING",
                    succeeded=task_num == 1,
                )
                attempt_repo.save(attempt)

            event_repo = ExecutionEventRepository(session)
            events = [
                ("RUN_STARTED", None),
                ("TASK_PENDING", "task-1"),
                ("TASK_RUNNING", "task-1"),
                ("TASK_SUCCEEDED", "task-1"),
                ("TASK_PENDING", "task-2"),
                ("TASK_RUNNING", "task-2"),
            ]
            base_time = datetime.utcnow()
            for i, (event_type, task_id) in enumerate(events):
                event = ExecutionEventModel(
                    event_id=f"event-{i}",
                    run_id="run-1",
                    task_id=task_id,
                    event_type=event_type,
                    timestamp=base_time + timedelta(milliseconds=i),
                )
                event_repo.save(event)

        with temp_db.get_session() as session:
            manager = CrashRecoveryManager(session)
            result = manager.recover_run("run-1")

            assert result.recovered is True
            assert result.preserved_tasks == 1  # task-1 completed
            assert result.requeued_tasks == 1  # task-2 in progress
            assert len([d for d in result.decisions if d.action == RecoveryAction.PRESERVE]) == 1
            assert len([d for d in result.decisions if d.action == RecoveryAction.REQUEUE]) == 1

    def test_mark_unsafe_tasks_as_failed(self, temp_db) -> None:
        """Should mark unsafe/incomplete tasks as failed."""
        with temp_db.get_session() as session:
            run_repo = ExecutionRunRepository(session)
            run_repo.save(run_id="run-1", workflow_id="wf-recovery", state="RUNNING")

            attempt_repo = TaskAttemptRepository(session)
            # Task with no events - unsafe state
            attempt = TaskAttemptModel(
                attempt_id="attempt-1",
                run_id="run-1",
                task_id="task-1",
                attempt_number=1,
                state="UNKNOWN",
            )
            attempt_repo.save(attempt)

            event_repo = ExecutionEventRepository(session)
            event = ExecutionEventModel(
                event_id="event-1",
                run_id="run-1",
                event_type="RUN_STARTED",
            )
            event_repo.save(event)

        with temp_db.get_session() as session:
            manager = CrashRecoveryManager(session)
            result = manager.recover_run("run-1")

            assert result.recovered is True
            assert result.failed_tasks == 1
            failed_decision = [
                d for d in result.decisions if d.action == RecoveryAction.MARK_FAILED
            ][0]
            assert failed_decision.recovery_state == RecoveryState.UNSAFE

    def test_get_completed_tasks(self, temp_db) -> None:
        """Should retrieve completed tasks from run state."""
        with temp_db.get_session() as session:
            run_repo = ExecutionRunRepository(session)
            run_repo.save(run_id="run-1", workflow_id="wf-recovery", state="SUCCEEDED")

            attempt_repo = TaskAttemptRepository(session)
            for task_num in [1, 2, 3]:
                state = "SUCCEEDED" if task_num <= 2 else "FAILED"
                attempt = TaskAttemptModel(
                    attempt_id=f"attempt-{task_num}",
                    run_id="run-1",
                    task_id=f"task-{task_num}",
                    attempt_number=1,
                    state=state,
                )
                attempt_repo.save(attempt)

            event_repo = ExecutionEventRepository(session)
            base_time = datetime.utcnow()
            for task_num in [1, 2, 3]:
                event_type = "TASK_SUCCEEDED" if task_num <= 2 else "TASK_FAILED"
                event = ExecutionEventModel(
                    event_id=f"event-task-{task_num}",
                    run_id="run-1",
                    task_id=f"task-{task_num}",
                    event_type=event_type,
                    timestamp=base_time + timedelta(milliseconds=task_num),
                )
                event_repo.save(event)

        with temp_db.get_session() as session:
            manager = CrashRecoveryManager(session)
            completed = manager.get_completed_tasks("run-1")

            assert "task-1" in completed
            assert "task-2" in completed
            assert "task-3" not in completed
            assert len(completed) == 2

    def test_get_tasks_to_requeue(self, temp_db) -> None:
        """Should identify tasks safe to requeue."""
        with temp_db.get_session() as session:
            run_repo = ExecutionRunRepository(session)
            run_repo.save(run_id="run-1", workflow_id="wf-recovery", state="RUNNING")

            attempt_repo = TaskAttemptRepository(session)
            for task_num in [1, 2]:
                attempt = TaskAttemptModel(
                    attempt_id=f"attempt-{task_num}",
                    run_id="run-1",
                    task_id=f"task-{task_num}",
                    attempt_number=1,
                    state="RUNNING",
                )
                attempt_repo.save(attempt)

            event_repo = ExecutionEventRepository(session)
            base_time = datetime.utcnow()
            event_counter = 0
            for task_num in [1, 2]:
                for event_type in ["TASK_PENDING", "TASK_RUNNING"]:
                    event = ExecutionEventModel(
                        event_id=f"event-{task_num}-{event_type}",
                        run_id="run-1",
                        task_id=f"task-{task_num}",
                        event_type=event_type,
                        timestamp=base_time + timedelta(milliseconds=event_counter),
                    )
                    event_repo.save(event)
                    event_counter += 1

        with temp_db.get_session() as session:
            manager = CrashRecoveryManager(session)
            to_requeue = manager.get_tasks_to_requeue("run-1")

            assert "task-1" in to_requeue
            assert "task-2" in to_requeue
            assert len(to_requeue) == 2


class TestReconciliationService:
    """Tests for reconciliation and recovery diagnostics."""

    def test_reconcile_run_with_audit_trail(self, temp_db) -> None:
        """Should reconcile run with complete audit trail."""
        from helixops.recovery.reconciliation import ReconciliationService

        with temp_db.get_session() as session:
            run_repo = ExecutionRunRepository(session)
            run_repo.save(run_id="run-1", workflow_id="wf-recovery", state="RUNNING")

            attempt_repo = TaskAttemptRepository(session)
            attempt = TaskAttemptModel(
                attempt_id="attempt-1",
                run_id="run-1",
                task_id="task-1",
                attempt_number=1,
                state="RUNNING",
            )
            attempt_repo.save(attempt)

            event_repo = ExecutionEventRepository(session)
            base_time = datetime.utcnow()
            for i, event_type in enumerate(["RUN_STARTED", "TASK_PENDING", "TASK_RUNNING"]):
                event = ExecutionEventModel(
                    event_id=f"event-{event_type}",
                    run_id="run-1",
                    task_id="task-1" if event_type.startswith("TASK") else None,
                    event_type=event_type,
                    timestamp=base_time + timedelta(milliseconds=i),
                )
                event_repo.save(event)

        with temp_db.get_session() as session:
            service = ReconciliationService(session)
            result = service.reconcile_run("run-1")

            assert result["recovered"] is True
            assert result["statistics"]["requeued"] == 1
            assert "report" in result
            assert "diagnostics" in result

    def test_reconciliation_summary(self, temp_db) -> None:
        """Should generate reconciliation summary."""
        from helixops.recovery.reconciliation import ReconciliationService

        with temp_db.get_session() as session:
            run_repo = ExecutionRunRepository(session)
            for i in range(2):
                run_repo.save(run_id=f"run-{i}", workflow_id="wf-recovery", state="RUNNING")

            attempt_repo = TaskAttemptRepository(session)
            for i in range(2):
                attempt = TaskAttemptModel(
                    attempt_id=f"attempt-{i}",
                    run_id=f"run-{i}",
                    task_id=f"task-{i}",
                    attempt_number=1,
                    state="RUNNING",
                )
                attempt_repo.save(attempt)

            event_repo = ExecutionEventRepository(session)
            base_time = datetime.utcnow()
            for run_idx in range(2):
                for i, event_type in enumerate(["RUN_STARTED", "TASK_PENDING", "TASK_RUNNING"]):
                    event = ExecutionEventModel(
                        event_id=f"event-{run_idx}-{event_type}",
                        run_id=f"run-{run_idx}",
                        task_id=f"task-{run_idx}" if event_type.startswith("TASK") else None,
                        event_type=event_type,
                        timestamp=base_time + timedelta(milliseconds=run_idx * 100 + i),
                    )
                    event_repo.save(event)

        with temp_db.get_session() as session:
            service = ReconciliationService(session)
            # Reconcile both runs
            for i in range(2):
                service.reconcile_run(f"run-{i}")

            summary = service.get_reconciliation_summary()

            assert summary["unique_runs_reconciled"] == 2
            assert summary["task_decisions_made"] >= 2


class TestRecoveryAuditTrail:
    """Tests for recovery audit trail."""

    def test_log_recovery_decision(self) -> None:
        """Should log recovery decisions."""
        from helixops.recovery.models import TaskRecoveryDecision

        trail = RecoveryAuditTrail()
        decision = TaskRecoveryDecision(
            task_id="task-1",
            recovery_state=RecoveryState.COMPLETED,
            action=RecoveryAction.PRESERVE,
            reason="Task completed successfully",
            is_safe=True,
        )

        event = trail.log_recovery_decision("run-1", decision)

        assert event.task_id == "task-1"
        assert event.action == RecoveryAction.PRESERVE
        assert event.run_id == "run-1"

    def test_get_run_audit_trail(self) -> None:
        """Should retrieve audit trail for run."""
        from helixops.recovery.models import TaskRecoveryDecision

        trail = RecoveryAuditTrail()
        trail.log_run_recovery_start("run-1")

        for i in range(3):
            decision = TaskRecoveryDecision(
                task_id=f"task-{i}",
                recovery_state=RecoveryState.COMPLETED,
                action=RecoveryAction.PRESERVE,
                reason="Completed",
                is_safe=True,
            )
            trail.log_recovery_decision("run-1", decision)

        trail.log_run_recovery_complete("run-1", True, {"preserved": 3})

        events = trail.get_run_audit_trail("run-1")
        assert len(events) == 5  # 1 start + 3 decisions + 1 complete

    def test_recovery_diagnostics(self) -> None:
        """Should generate recovery diagnostics."""
        from helixops.recovery.models import TaskRecoveryDecision

        trail = RecoveryAuditTrail()
        trail.log_run_recovery_start("run-1")

        for i in range(2):
            decision = TaskRecoveryDecision(
                task_id=f"task-{i}",
                recovery_state=RecoveryState.COMPLETED,
                action=RecoveryAction.PRESERVE,
                reason="Completed",
                is_safe=True,
            )
            trail.log_recovery_decision("run-1", decision)

        trail.log_run_recovery_complete("run-1", True, {"preserved": 2})

        diag = trail.get_recovery_diagnostics("run-1")

        assert diag["run_id"] == "run-1"
        assert diag["recovery_events"] == 4
        assert diag["task_decisions"] == 2
        assert "preserve" in diag["action_summary"]

    def test_generate_recovery_report(self) -> None:
        """Should generate human-readable recovery report."""
        from helixops.recovery.models import TaskRecoveryDecision

        trail = RecoveryAuditTrail()
        trail.log_run_recovery_start("run-1")

        decision = TaskRecoveryDecision(
            task_id="task-1",
            recovery_state=RecoveryState.COMPLETED,
            action=RecoveryAction.PRESERVE,
            reason="Task completed",
            is_safe=True,
        )
        trail.log_recovery_decision("run-1", decision)

        report = trail.generate_recovery_report("run-1")

        assert "Recovery Report" in report
        assert "run-1" in report
        assert "task-1" in report
        assert "preserve" in report.lower()

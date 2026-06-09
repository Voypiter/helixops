"""Reconciliation and recovery diagnostics service."""

from typing import Any

from sqlalchemy.orm import Session

from helixops.recovery.audit import RecoveryAuditTrail
from helixops.recovery.manager import CrashRecoveryManager
from helixops.storage.repository import ExecutionRunRepository


class ReconciliationService:
    """Service for comprehensive run reconciliation and recovery diagnostics."""

    def __init__(self, session: Session) -> None:
        """Initialize reconciliation service.

        Args:
            session: SQLAlchemy session for database access
        """
        self.session = session
        self.recovery_manager = CrashRecoveryManager(session)
        self.audit_trail = RecoveryAuditTrail()
        self.runs = ExecutionRunRepository(session)

    def reconcile_run(self, run_id: str) -> dict[str, Any]:
        """Reconcile and recover a run, with full audit trail.

        Args:
            run_id: Run identifier to reconcile

        Returns:
            Dictionary with reconciliation details and audit trail
        """
        # Log recovery start
        self.audit_trail.log_run_recovery_start(run_id)

        # Perform recovery
        result = self.recovery_manager.recover_run(run_id)

        # Log all decisions
        for decision in result.decisions:
            self.audit_trail.log_recovery_decision(run_id, decision)

        # Log completion
        stats = {
            "preserved": result.preserved_tasks,
            "requeued": result.requeued_tasks,
            "failed": result.failed_tasks,
            "total_decisions": result.total_decisions,
        }
        self.audit_trail.log_run_recovery_complete(run_id, result.recovered, stats)

        # Generate report
        report = self.audit_trail.generate_recovery_report(run_id)
        diagnostics = self.audit_trail.get_recovery_diagnostics(run_id)

        return {
            "run_id": run_id,
            "recovered": result.recovered,
            "decisions": result.decisions,
            "statistics": stats,
            "diagnostics": diagnostics,
            "report": report,
        }

    def reconcile_workflows(self, workflow_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Reconcile multiple workflows.

        Args:
            workflow_ids: List of workflow identifiers

        Returns:
            Dictionary mapping workflow IDs to reconciliation results
        """
        results = {}
        for _workflow_id in workflow_ids:
            # Get all runs for this workflow
            all_runs = self.runs.session.query(  # type: ignore[call-overload]
                "SELECT run_id FROM execution_runs WHERE workflow_id = ?"
            ).all()

            for run_tuple in all_runs:
                run_id = run_tuple[0]
                try:
                    results[run_id] = self.reconcile_run(run_id)
                except Exception as e:
                    results[run_id] = {
                        "run_id": run_id,
                        "recovered": False,
                        "error": str(e),
                    }

        return results

    def get_reconciliation_summary(self) -> dict[str, Any]:
        """Get summary of all reconciliation operations.

        Returns:
            Summary statistics across all reconciliations
        """
        all_trails = self.audit_trail.events

        total_events = len(all_trails)
        unique_runs = len({e.run_id for e in all_trails})
        task_decisions = len({e.event_id for e in all_trails if e.task_id})

        action_summary: dict[str, int] = {}
        for event in all_trails:
            action = event.action.value
            action_summary[action] = action_summary.get(action, 0) + 1

        return {
            "total_recovery_events": total_events,
            "unique_runs_reconciled": unique_runs,
            "task_decisions_made": task_decisions,
            "action_summary": action_summary,
        }

    def export_reconciliation_history(self) -> list[dict[str, Any]]:
        """Export full reconciliation history for audit.

        Returns:
            List of reconciliation events as dictionaries
        """
        return [
            {
                "event_id": e.event_id,
                "run_id": e.run_id,
                "task_id": e.task_id,
                "action": e.action.value,
                "reason": e.reason,
                "timestamp": e.timestamp.isoformat(),
                "state": e.decision_state.value,
            }
            for e in self.audit_trail.events
        ]

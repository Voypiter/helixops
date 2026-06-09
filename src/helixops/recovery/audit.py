"""Recovery audit trail and reconciliation diagnostics."""

from typing import Any
from uuid import uuid4

from helixops.recovery.models import (
    RecoveryAction,
    RecoveryAuditEvent,
    RecoveryState,
    TaskRecoveryDecision,
)


class RecoveryAuditTrail:
    """Maintains audit trail of recovery actions for diagnostics."""

    def __init__(self) -> None:
        """Initialize audit trail."""
        self.events: list[RecoveryAuditEvent] = []

    def log_recovery_decision(
        self,
        run_id: str,
        decision: TaskRecoveryDecision,
        reason_detail: str = "",
    ) -> RecoveryAuditEvent:
        """Log a recovery decision.

        Args:
            run_id: Run identifier
            decision: Recovery decision
            reason_detail: Additional context

        Returns:
            Logged audit event
        """
        event = RecoveryAuditEvent(
            event_id=str(uuid4()),
            run_id=run_id,
            task_id=decision.task_id,
            action=decision.action,
            reason=decision.reason,
            decision_state=decision.recovery_state,
            metadata={
                "is_safe": decision.is_safe,
                "attempt_number": decision.attempt_number,
                "detail": reason_detail,
            },
        )
        self.events.append(event)
        return event

    def log_run_recovery_start(self, run_id: str) -> RecoveryAuditEvent:
        """Log start of run recovery.

        Args:
            run_id: Run identifier

        Returns:
            Logged audit event
        """
        event = RecoveryAuditEvent(
            event_id=str(uuid4()),
            run_id=run_id,
            task_id=None,
            action=RecoveryAction.PRESERVE,
            reason="Run recovery initiated",
            decision_state=RecoveryState.UNKNOWN,
            metadata={"event_type": "recovery_start"},
        )
        self.events.append(event)
        return event

    def log_run_recovery_complete(
        self,
        run_id: str,
        success: bool,
        stats: dict[str, Any],
    ) -> RecoveryAuditEvent:
        """Log completion of run recovery.

        Args:
            run_id: Run identifier
            success: Whether recovery was successful
            stats: Recovery statistics

        Returns:
            Logged audit event
        """
        event = RecoveryAuditEvent(
            event_id=str(uuid4()),
            run_id=run_id,
            task_id=None,
            action=RecoveryAction.PRESERVE,
            reason="Run recovery completed",
            decision_state=RecoveryState.COMPLETED if success else RecoveryState.UNKNOWN,
            metadata={
                "event_type": "recovery_complete",
                "success": success,
                "stats": stats,
            },
        )
        self.events.append(event)
        return event

    def get_run_audit_trail(self, run_id: str) -> list[RecoveryAuditEvent]:
        """Get all audit events for a run.

        Args:
            run_id: Run identifier

        Returns:
            List of audit events chronologically ordered
        """
        return sorted(
            [e for e in self.events if e.run_id == run_id],
            key=lambda e: e.timestamp,
        )

    def get_recovery_diagnostics(self, run_id: str) -> dict[str, Any]:
        """Get diagnostic summary of recovery operations.

        Args:
            run_id: Run identifier

        Returns:
            Dictionary with recovery diagnostics
        """
        trail = self.get_run_audit_trail(run_id)

        if not trail:
            return {"run_id": run_id, "recovery_events": 0}

        start_time = trail[0].timestamp
        end_time = trail[-1].timestamp
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        action_counts: dict[str, int] = {}
        state_counts: dict[str, int] = {}

        for event in trail:
            action = event.action.value
            state = event.decision_state.value

            action_counts[action] = action_counts.get(action, 0) + 1
            state_counts[state] = state_counts.get(state, 0) + 1

        return {
            "run_id": run_id,
            "recovery_events": len(trail),
            "duration_ms": duration_ms,
            "start_time": start_time,
            "end_time": end_time,
            "action_summary": action_counts,
            "state_summary": state_counts,
            "task_decisions": len([e for e in trail if e.task_id is not None]),
        }

    def generate_recovery_report(self, run_id: str) -> str:
        """Generate a human-readable recovery report.

        Args:
            run_id: Run identifier

        Returns:
            Formatted recovery report
        """
        trail = self.get_run_audit_trail(run_id)
        diagnostics = self.get_recovery_diagnostics(run_id)

        if not trail:
            return f"No recovery events for run {run_id}"

        lines = [
            f"Recovery Report for Run: {run_id}",
            "=" * 60,
            f"Total Events: {diagnostics['recovery_events']}",
            f"Duration: {diagnostics['duration_ms']}ms",
            f"Task Decisions: {diagnostics['task_decisions']}",
            "",
            "Action Summary:",
        ]

        for action, count in diagnostics["action_summary"].items():
            lines.append(f"  {action}: {count}")

        lines.append("")
        lines.append("State Summary:")
        for state, count in diagnostics["state_summary"].items():
            lines.append(f"  {state}: {count}")

        lines.append("")
        lines.append("Decision History:")
        for event in trail:
            if event.task_id:
                lines.append(
                    f"  [{event.timestamp.isoformat()}] Task {event.task_id}: "
                    f"{event.action.value} ({event.reason})"
                )
            else:
                lines.append(f"  [{event.timestamp.isoformat()}] {event.reason}")

        return "\n".join(lines)

"""Event journal for audit trails and recovery."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from helixops.storage.models import ExecutionEventModel
from helixops.storage.repository import ExecutionEventRepository


class EventJournal:
    """Transactional event journal for execution audit trails."""

    def __init__(self, session: Session):
        """Initialize event journal with database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session
        self.event_repo = ExecutionEventRepository(session)

    def get_run_timeline(self, run_id: str) -> List[ExecutionEventModel]:
        """Get complete event timeline for a run in chronological order.

        Args:
            run_id: Run identifier

        Returns:
            List of events ordered by timestamp
        """
        return self.event_repo.get_by_run(run_id)

    def get_task_timeline(self, attempt_id: str) -> List[ExecutionEventModel]:
        """Get event timeline for a specific task attempt.

        Args:
            attempt_id: Task attempt identifier

        Returns:
            List of events for the attempt ordered by timestamp
        """
        return self.event_repo.get_by_task(attempt_id)

    def get_events_since(
        self, run_id: str, timestamp: datetime
    ) -> List[ExecutionEventModel]:
        """Get events after a specific timestamp.

        Args:
            run_id: Run identifier
            timestamp: Starting timestamp (exclusive)

        Returns:
            List of events after the timestamp
        """
        all_events = self.event_repo.get_by_run(run_id)
        return [e for e in all_events if e.timestamp > timestamp]

    def get_events_by_type(
        self, run_id: str, event_type: str
    ) -> List[ExecutionEventModel]:
        """Get all events of a specific type in a run.

        Args:
            run_id: Run identifier
            event_type: Event type filter

        Returns:
            List of matching events
        """
        all_events = self.event_repo.get_by_run(run_id)
        return [e for e in all_events if e.event_type == event_type]

    def get_failure_events(self, run_id: str) -> List[ExecutionEventModel]:
        """Get all failure-related events in a run.

        Args:
            run_id: Run identifier

        Returns:
            List of failure events
        """
        all_events = self.event_repo.get_by_run(run_id)
        failure_types = {"TASK_FAILED", "RUN_FAILED", "TASK_TIMED_OUT"}
        return [e for e in all_events if e.event_type in failure_types]

    def verify_event_completeness(self, run_id: str) -> dict:
        """Verify event journal completeness and consistency.

        Args:
            run_id: Run identifier

        Returns:
            Dictionary with completeness metrics
        """
        events = self.event_repo.get_by_run(run_id)

        event_types = {e.event_type for e in events}
        has_start = "RUN_STARTED" in event_types or "RUN_RUNNING" in event_types
        has_end = "RUN_SUCCEEDED" in event_types or "RUN_FAILED" in event_types or "RUN_CANCELLED" in event_types

        return {
            "total_events": len(events),
            "unique_event_types": len(event_types),
            "has_run_start": has_start,
            "has_run_end": has_end,
            "is_complete": has_start and has_end,
        }

"""Recovery and reconciliation data models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Set, Optional
from datetime import datetime


class RecoveryState(Enum):
    """Task state classification for recovery."""

    SAFE_TO_RESUME = "safe_to_resume"
    COMPLETED = "completed"
    FAILED = "failed"
    UNSAFE = "unsafe"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """Action to take for a recovered task."""

    PRESERVE = "preserve"
    REQUEUE = "requeue"
    MARK_FAILED = "mark_failed"
    MARK_SKIPPED = "mark_skipped"
    CANCEL = "cancel"


@dataclass
class TaskRecoveryDecision:
    """Recovery decision for a single task."""

    task_id: str
    recovery_state: RecoveryState
    action: RecoveryAction
    reason: str
    is_safe: bool
    attempt_number: int = 1


@dataclass
class RunRecoveryState:
    """Recovery state classification for a run."""

    run_id: str
    workflow_id: str
    is_complete: bool
    incomplete_tasks: List[str] = field(default_factory=list)
    in_progress_tasks: List[str] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    unknown_tasks: List[str] = field(default_factory=list)
    total_event_count: int = 0
    has_run_start: bool = False
    has_run_end: bool = False
    last_event_timestamp: Optional[datetime] = None


@dataclass
class RecoveryResult:
    """Result of crash recovery operation."""

    run_id: str
    recovered: bool
    decisions: List[TaskRecoveryDecision] = field(default_factory=list)
    preserved_tasks: int = 0
    requeued_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    total_decisions: int = 0
    recovery_errors: List[str] = field(default_factory=list)


@dataclass
class RecoveryAuditEvent:
    """Audit trail entry for recovery actions."""

    event_id: str
    run_id: str
    task_id: Optional[str]
    action: RecoveryAction
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    decision_state: RecoveryState = RecoveryState.UNKNOWN
    metadata: Dict = field(default_factory=dict)

"""Failure classification and semantics."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FailureClass(Enum):
    """Classification of failure types."""
    TRANSIENT = "transient"  # Recoverable with retry
    PERMANENT = "permanent"  # Not recoverable
    DEPENDENCY = "dependency"  # Dependency failure blocked this task
    TIMEOUT = "timeout"  # Task exceeded timeout
    CANCELLED = "cancelled"  # Task was cancelled
    POISON = "poison"  # Task is marked as poison (don't retry)


@dataclass
class FailureClassification:
    """Classification of a task failure."""
    failure_class: FailureClass
    retryable: bool
    error_message: str
    root_cause: Optional[str] = None
    suggests_poison: bool = False

    @staticmethod
    def classify_from_error(error_message: str, attempt_count: int = 1) -> "FailureClassification":
        """Classify a failure from an error message."""
        lower_msg = error_message.lower()

        # Check for poison markers
        if "poison" in lower_msg or "fatal" in lower_msg:
            return FailureClassification(
                failure_class=FailureClass.POISON,
                retryable=False,
                error_message=error_message,
                suggests_poison=True,
            )

        # Timeout
        if "timeout" in lower_msg or "timed out" in lower_msg:
            return FailureClassification(
                failure_class=FailureClass.TIMEOUT,
                retryable=True,
                error_message=error_message,
            )

        # Cancelled
        if "cancel" in lower_msg or "abort" in lower_msg:
            return FailureClassification(
                failure_class=FailureClass.CANCELLED,
                retryable=False,
                error_message=error_message,
            )

        # Transient errors (typically retriable)
        transient_keywords = [
            "connection",
            "network",
            "temporarily",
            "unavailable",
            "busy",
            "retry",
            "transient",
            "throttle",
        ]
        if any(keyword in lower_msg for keyword in transient_keywords):
            return FailureClassification(
                failure_class=FailureClass.TRANSIENT,
                retryable=True,
                error_message=error_message,
            )

        # Dependency failure (but don't retry this task, cascade the failure)
        if "dependency" in lower_msg or "upstream" in lower_msg:
            return FailureClassification(
                failure_class=FailureClass.DEPENDENCY,
                retryable=False,
                error_message=error_message,
            )

        # Default: treat as permanent (safe default)
        return FailureClassification(
            failure_class=FailureClass.PERMANENT,
            retryable=False,
            error_message=error_message,
        )

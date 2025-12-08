"""Domain-specific exceptions."""


class HelixOpsError(Exception):
    """Base exception for all HelixOps errors."""

    pass


class ValidationError(HelixOpsError):
    """Raised when domain validation fails."""

    pass


class DuplicateTaskError(ValidationError):
    """Raised when a workflow contains duplicate task IDs."""

    pass


class MissingDependencyError(ValidationError):
    """Raised when a task depends on a non-existent task."""

    pass


class CyclicDependencyError(ValidationError):
    """Raised when the dependency graph contains cycles."""

    pass


class InvalidRetryPolicyError(ValidationError):
    """Raised when a retry policy has invalid parameters."""

    pass


class InvalidTimeoutError(ValidationError):
    """Raised when a timeout value is impossible."""

    pass


class IllegalStateTransitionError(HelixOpsError):
    """Raised when an illegal state transition is attempted."""

    pass


class WorkflowError(HelixOpsError):
    """Raised for general workflow errors."""

    pass

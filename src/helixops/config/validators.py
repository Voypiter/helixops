"""Input validation and safety limit enforcement."""

from typing import Any, Dict, List
from helixops.config.settings import get_config


class ValidationError(Exception):
    """Validation constraint violated."""

    pass


class InputValidator:
    """Validates user inputs against safety constraints."""

    @staticmethod
    def validate_workflow_size(task_count: int) -> None:
        """Check task count against limits.

        Args:
            task_count: Number of tasks

        Raises:
            ValidationError: If task count exceeds limit
        """
        config = get_config()
        if task_count > config.security.max_task_count:
            raise ValidationError(
                f"Task count {task_count} exceeds limit {config.security.max_task_count}"
            )

    @staticmethod
    def validate_concurrency(max_concurrent: int) -> None:
        """Check concurrency setting against limits.

        Args:
            max_concurrent: Max concurrent tasks

        Raises:
            ValidationError: If concurrency exceeds limit
        """
        config = get_config()
        if max_concurrent > config.execution.max_concurrent_limit:
            raise ValidationError(
                f"Concurrency {max_concurrent} exceeds limit {config.execution.max_concurrent_limit}"
            )
        if max_concurrent < 1:
            raise ValidationError("Concurrency must be >= 1")

    @staticmethod
    def validate_timeout(timeout_seconds: int) -> None:
        """Check timeout against limits.

        Args:
            timeout_seconds: Task timeout in seconds

        Raises:
            ValidationError: If timeout is invalid
        """
        config = get_config()
        if timeout_seconds <= 0:
            raise ValidationError("Timeout must be positive")
        if timeout_seconds > config.execution.task_timeout_seconds:
            raise ValidationError(
                f"Timeout {timeout_seconds}s exceeds limit {config.execution.task_timeout_seconds}s"
            )

    @staticmethod
    def validate_pagination(skip: int, limit: int) -> None:
        """Check pagination parameters.

        Args:
            skip: Records to skip
            limit: Records to return

        Raises:
            ValidationError: If pagination parameters are invalid
        """
        config = get_config()
        if skip < 0:
            raise ValidationError("skip must be >= 0")
        if limit < 1:
            raise ValidationError("limit must be >= 1")
        if limit > config.api.pagination_max_limit:
            raise ValidationError(
                f"limit {limit} exceeds max {config.api.pagination_max_limit}"
            )

    @staticmethod
    def validate_workflow_definition(workflow_dict: Dict[str, Any]) -> None:
        """Validate workflow definition structure.

        Args:
            workflow_dict: Workflow definition

        Raises:
            ValidationError: If workflow definition is invalid
        """
        config = get_config()

        if not isinstance(workflow_dict, dict):
            raise ValidationError("Workflow must be a dictionary")

        if "tasks" not in workflow_dict:
            raise ValidationError("Workflow missing 'tasks' field")

        tasks = workflow_dict["tasks"]
        if not isinstance(tasks, dict):
            raise ValidationError("Workflow 'tasks' must be a dictionary")

        task_count = len(tasks)
        if task_count > config.security.max_task_count:
            raise ValidationError(
                f"Workflow has {task_count} tasks, max is {config.security.max_task_count}"
            )

        if config.security.input_validation_strict:
            # Validate task structure
            for task_id, task_def in tasks.items():
                if not isinstance(task_id, str):
                    raise ValidationError(f"Task ID must be string, got {type(task_id)}")
                if not task_id.replace("_", "").replace("-", "").isalnum():
                    raise ValidationError(
                        f"Task ID '{task_id}' contains invalid characters"
                    )


class RateLimiter:
    """Rate limiting for API endpoints."""

    def __init__(self, requests_per_minute: int = 1000):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Max requests per minute
        """
        self.max_requests = requests_per_minute
        self.window_seconds = 60
        self.request_times: List[float] = []

    def is_allowed(self, timestamp: float) -> bool:
        """Check if request is allowed.

        Args:
            timestamp: Request timestamp

        Returns:
            True if request is within rate limit
        """
        # Remove old entries outside window
        self.request_times = [
            t for t in self.request_times
            if timestamp - t < self.window_seconds
        ]

        if len(self.request_times) >= self.max_requests:
            return False

        self.request_times.append(timestamp)
        return True


class SafetyLimits:
    """Runtime safety enforcement."""

    @staticmethod
    def enforce_request_size(content_length: int) -> None:
        """Check request size against limits.

        Args:
            content_length: Request size in bytes

        Raises:
            ValidationError: If request too large
        """
        config = get_config()
        max_bytes = config.api.max_request_size_mb * 1024 * 1024

        if content_length > max_bytes:
            raise ValidationError(
                f"Request size {content_length} bytes exceeds limit {max_bytes}"
            )

    @staticmethod
    def enforce_event_retention(event_count: int) -> bool:
        """Check if event retention limit reached.

        Args:
            event_count: Current event count

        Returns:
            True if under limit
        """
        config = get_config()
        return event_count < config.observability.max_events_in_memory

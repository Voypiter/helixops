"""Retry policy engine with backoff calculation."""

import random


class RetryPolicyEngine:
    """Manages retry decisions and backoff calculation."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_backoff_ms: int = 100,
        max_backoff_ms: int = 30000,
        backoff_multiplier: float = 2.0,
        jitter_factor: float = 0.1,
        seed: int | None = None,
    ):
        self.max_attempts = max_attempts
        self.initial_backoff_ms = initial_backoff_ms
        self.max_backoff_ms = max_backoff_ms
        self.backoff_multiplier = backoff_multiplier
        self.jitter_factor = jitter_factor

        if seed is not None:
            random.seed(seed)

        self._validate()

    def _validate(self) -> None:
        """Validate policy parameters."""
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")
        if self.initial_backoff_ms < 0:
            raise ValueError(f"initial_backoff_ms must be >= 0, got {self.initial_backoff_ms}")
        if self.max_backoff_ms < self.initial_backoff_ms:
            raise ValueError("max_backoff_ms must be >= initial_backoff_ms")
        if self.backoff_multiplier <= 1.0:
            raise ValueError(f"backoff_multiplier must be > 1.0, got {self.backoff_multiplier}")
        if not (0 <= self.jitter_factor <= 1.0):
            raise ValueError(f"jitter_factor must be in [0, 1.0], got {self.jitter_factor}")

    def should_retry(self, attempt_count: int, retryable: bool) -> bool:
        """Determine if a task should be retried."""
        if not retryable:
            return False

        return attempt_count < self.max_attempts

    def get_backoff_ms(self, attempt_count: int) -> int:
        """Calculate backoff delay in milliseconds for the given attempt number."""
        if attempt_count <= 0:
            return 0

        # Exponential backoff: initial_backoff * (multiplier ^ (attempt - 1))
        base_backoff = self.initial_backoff_ms * (self.backoff_multiplier ** (attempt_count - 1))

        # Cap at max
        base_backoff = min(base_backoff, self.max_backoff_ms)

        # Add jitter
        jitter_amount = base_backoff * self.jitter_factor
        jitter = random.uniform(-jitter_amount, jitter_amount)
        backoff_with_jitter = base_backoff + jitter

        # Ensure non-negative
        return max(0, int(backoff_with_jitter))

    def get_max_attempts(self) -> int:
        """Get the maximum number of attempts."""
        return self.max_attempts

    def is_final_attempt(self, attempt_count: int) -> bool:
        """Check if this is the final attempt."""
        return attempt_count >= self.max_attempts

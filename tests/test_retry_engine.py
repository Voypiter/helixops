"""Tests for retry policy and failure classification."""

import pytest

from helixops.retry.policy import RetryPolicyEngine
from helixops.retry.failures import FailureClass, FailureClassification


class TestFailureClassification:
    """Tests for failure classification."""

    def test_classify_transient_error(self) -> None:
        """Transient errors should be retryable."""
        result = FailureClassification.classify_from_error(
            "Connection refused - temporarily unavailable"
        )

        assert result.failure_class == FailureClass.TRANSIENT
        assert result.retryable is True

    def test_classify_timeout_error(self) -> None:
        """Timeout errors should be retryable."""
        result = FailureClassification.classify_from_error("Task timed out after 30s")

        assert result.failure_class == FailureClass.TIMEOUT
        assert result.retryable is True

    def test_classify_permanent_error(self) -> None:
        """Permanent errors should not be retryable."""
        result = FailureClassification.classify_from_error(
            "Invalid input parameter provided"
        )

        assert result.failure_class == FailureClass.PERMANENT
        assert result.retryable is False

    def test_classify_cancelled(self) -> None:
        """Cancelled tasks should not be retried."""
        result = FailureClassification.classify_from_error("Task was cancelled")

        assert result.failure_class == FailureClass.CANCELLED
        assert result.retryable is False

    def test_classify_poison_task(self) -> None:
        """Poison tasks should be marked as non-retriable."""
        result = FailureClassification.classify_from_error(
            "Fatal error - poison task"
        )

        assert result.failure_class == FailureClass.POISON
        assert result.retryable is False
        assert result.suggests_poison is True

    def test_classify_dependency_failure(self) -> None:
        """Dependency failures should not retry but cascade."""
        result = FailureClassification.classify_from_error(
            "Upstream dependency failed"
        )

        assert result.failure_class == FailureClass.DEPENDENCY
        assert result.retryable is False

    def test_classify_network_error(self) -> None:
        """Network errors should be transient."""
        result = FailureClassification.classify_from_error(
            "Network unavailable temporarily"
        )

        assert result.failure_class == FailureClass.TRANSIENT
        assert result.retryable is True


class TestRetryPolicyEngine:
    """Tests for retry policy engine."""

    def test_valid_policy_creation(self) -> None:
        """Valid policy should be created."""
        policy = RetryPolicyEngine(
            max_attempts=3,
            initial_backoff_ms=100,
            max_backoff_ms=30000,
            backoff_multiplier=2.0,
            jitter_factor=0.1,
        )

        assert policy.max_attempts == 3
        assert policy.initial_backoff_ms == 100

    def test_invalid_max_attempts(self) -> None:
        """Invalid max_attempts should raise error."""
        with pytest.raises(ValueError):
            RetryPolicyEngine(max_attempts=0)

    def test_invalid_backoff_multiplier(self) -> None:
        """Invalid backoff_multiplier should raise error."""
        with pytest.raises(ValueError):
            RetryPolicyEngine(backoff_multiplier=1.0)

    def test_should_retry_with_retryable_failure(self) -> None:
        """Retryable failures should allow retries."""
        policy = RetryPolicyEngine(max_attempts=3)

        assert policy.should_retry(attempt_count=1, retryable=True)
        assert policy.should_retry(attempt_count=2, retryable=True)
        assert not policy.should_retry(attempt_count=3, retryable=True)

    def test_should_retry_with_non_retryable_failure(self) -> None:
        """Non-retryable failures should not retry."""
        policy = RetryPolicyEngine(max_attempts=3)

        assert not policy.should_retry(attempt_count=1, retryable=False)

    def test_backoff_increases_exponentially(self) -> None:
        """Backoff should increase exponentially."""
        policy = RetryPolicyEngine(
            max_attempts=5,
            initial_backoff_ms=100,
            max_backoff_ms=100000,
            backoff_multiplier=2.0,
            jitter_factor=0.0,  # No jitter for deterministic test
        )

        backoff_1 = policy.get_backoff_ms(1)
        backoff_2 = policy.get_backoff_ms(2)
        backoff_3 = policy.get_backoff_ms(3)

        # Should roughly double each time (with exact math)
        assert backoff_2 > backoff_1
        assert backoff_3 > backoff_2
        assert backoff_2 >= backoff_1 * 1.5  # At least 1.5x growth

    def test_backoff_capped_at_max(self) -> None:
        """Backoff should not exceed max."""
        policy = RetryPolicyEngine(
            max_attempts=10,
            initial_backoff_ms=100,
            max_backoff_ms=5000,
            backoff_multiplier=10.0,  # Aggressive multiplier
            jitter_factor=0.0,
        )

        for attempt in range(1, 10):
            backoff = policy.get_backoff_ms(attempt)
            assert backoff <= policy.max_backoff_ms

    def test_backoff_with_jitter(self) -> None:
        """Backoff with jitter should vary within bounds."""
        policy = RetryPolicyEngine(
            max_attempts=5,
            initial_backoff_ms=1000,
            max_backoff_ms=10000,
            backoff_multiplier=2.0,
            jitter_factor=0.5,
            seed=42,
        )

        backoffs = [policy.get_backoff_ms(1) for _ in range(10)]

        # Should not all be the same (due to jitter)
        assert len(set(backoffs)) > 1
        # Should be around 1000ms (with 50% jitter = 500-1500)
        assert all(500 <= b <= 1500 for b in backoffs)

    def test_deterministic_backoff_with_seed(self) -> None:
        """Backoff should be deterministic with same seed."""
        policy1 = RetryPolicyEngine(
            initial_backoff_ms=100,
            jitter_factor=0.5,
            seed=123,
        )

        backoffs1 = [policy1.get_backoff_ms(1) for _ in range(5)]

        # Reset and use same seed
        policy2 = RetryPolicyEngine(
            initial_backoff_ms=100,
            jitter_factor=0.5,
            seed=123,
        )

        backoffs2 = [policy2.get_backoff_ms(1) for _ in range(5)]

        assert backoffs1 == backoffs2

    def test_is_final_attempt(self) -> None:
        """Check if it's the final attempt."""
        policy = RetryPolicyEngine(max_attempts=3)

        assert not policy.is_final_attempt(1)
        assert not policy.is_final_attempt(2)
        assert policy.is_final_attempt(3)
        assert policy.is_final_attempt(4)

    def test_get_max_attempts(self) -> None:
        """Get max attempts from policy."""
        policy = RetryPolicyEngine(max_attempts=5)
        assert policy.get_max_attempts() == 5

    def test_zero_initial_backoff(self) -> None:
        """Policy with zero initial backoff should work."""
        policy = RetryPolicyEngine(initial_backoff_ms=0, jitter_factor=0.0)

        assert policy.get_backoff_ms(1) == 0

    def test_single_attempt_policy(self) -> None:
        """Policy with single attempt should not allow retry."""
        policy = RetryPolicyEngine(max_attempts=1)

        assert not policy.should_retry(attempt_count=1, retryable=True)

    def test_high_retry_attempts(self) -> None:
        """High retry attempts should work correctly."""
        policy = RetryPolicyEngine(max_attempts=10)

        for attempt in range(1, 10):
            assert policy.should_retry(attempt, retryable=True)

        assert not policy.should_retry(10, retryable=True)

    def test_realistic_exponential_backoff_sequence(self) -> None:
        """Test a realistic backoff sequence."""
        policy = RetryPolicyEngine(
            max_attempts=5,
            initial_backoff_ms=100,
            max_backoff_ms=10000,
            backoff_multiplier=2.0,
            jitter_factor=0.0,
        )

        backoffs = [policy.get_backoff_ms(i) for i in range(1, 6)]

        # Should be: 100, 200, 400, 800, 1600 (capped at 10000)
        assert backoffs[0] == 100
        assert backoffs[1] == 200
        assert backoffs[2] == 400
        assert backoffs[3] == 800
        assert backoffs[4] == 1600


class TestRetryPolicyIntegration:
    """Integration tests for retry policies with failure classification."""

    def test_transient_error_should_retry(self) -> None:
        """Transient errors should be retried according to policy."""
        policy = RetryPolicyEngine(max_attempts=3)
        classification = FailureClassification.classify_from_error(
            "Network temporarily unavailable"
        )

        assert policy.should_retry(attempt_count=1, retryable=classification.retryable)
        assert policy.should_retry(attempt_count=2, retryable=classification.retryable)
        assert not policy.should_retry(
            attempt_count=3, retryable=classification.retryable
        )

    def test_permanent_error_should_not_retry(self) -> None:
        """Permanent errors should not be retried."""
        policy = RetryPolicyEngine(max_attempts=3)
        classification = FailureClassification.classify_from_error(
            "Invalid configuration"
        )

        assert not policy.should_retry(
            attempt_count=1, retryable=classification.retryable
        )

    def test_timeout_error_retry_sequence(self) -> None:
        """Timeout errors should follow backoff sequence."""
        policy = RetryPolicyEngine(
            max_attempts=3,
            initial_backoff_ms=100,
            max_backoff_ms=1000,
            backoff_multiplier=2.0,
            jitter_factor=0.0,
        )
        classification = FailureClassification.classify_from_error("Task timed out")

        assert classification.retryable
        assert policy.should_retry(1, classification.retryable)

        backoff_1 = policy.get_backoff_ms(1)
        backoff_2 = policy.get_backoff_ms(2)

        assert backoff_2 > backoff_1

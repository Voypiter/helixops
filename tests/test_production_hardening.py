"""Tests for production hardening and safety features."""

import pytest
from helixops.config.settings import RuntimeConfig, DatabaseConfig, ExecutionConfig
from helixops.config.validators import InputValidator, ValidationError, RateLimiter, SafetyLimits
from helixops.service.lifecycle import LifecycleManager, ShutdownEvent
import time


class TestRuntimeConfig:
    """Tests for runtime configuration."""

    def test_default_config(self) -> None:
        """Should create default configuration."""
        config = RuntimeConfig()

        assert config.environment == "development"
        assert config.debug is False
        assert config.api.host == "127.0.0.1"
        assert config.api.port == 8000

    def test_config_from_environment(self, monkeypatch) -> None:
        """Should load config from environment variables."""
        monkeypatch.setenv("HELIXOPS_ENV", "production")
        monkeypatch.setenv("HELIXOPS_API_PORT", "9000")
        monkeypatch.setenv("HELIXOPS_DEBUG", "true")

        config = RuntimeConfig.from_environment()

        assert config.environment == "production"
        assert config.api.port == 9000
        assert config.debug is True

    def test_config_validation_concurrent(self) -> None:
        """Should validate concurrency limits."""
        config = RuntimeConfig()
        config.execution.max_concurrent_default = 600
        config.execution.max_concurrent_limit = 500

        with pytest.raises(ValueError, match="max_concurrent_default"):
            config.validate()

    def test_config_validation_port(self) -> None:
        """Should validate port in production."""
        config = RuntimeConfig()
        config.environment = "production"
        config.api.port = 80

        with pytest.raises(ValueError, match="port must be >= 1024"):
            config.validate()

    def test_production_config(self) -> None:
        """Should harden configuration for production."""
        config = RuntimeConfig()
        config = config.get_production_config()

        assert config.environment == "production"
        assert config.debug is False
        assert config.observability.metrics_enabled is True

    def test_database_config(self) -> None:
        """Should configure database safely."""
        config = DatabaseConfig()

        assert config.pool_size == 20
        assert config.migration_check is True
        assert config.echo is False


class TestInputValidator:
    """Tests for input validation."""

    def test_validate_workflow_size_ok(self) -> None:
        """Should accept valid task count."""
        InputValidator.validate_workflow_size(100)  # No exception

    def test_validate_workflow_size_exceeded(self) -> None:
        """Should reject excessive task count."""
        with pytest.raises(ValidationError, match="exceeds limit"):
            InputValidator.validate_workflow_size(50000)

    def test_validate_concurrency_ok(self) -> None:
        """Should accept valid concurrency."""
        InputValidator.validate_concurrency(50)  # No exception

    def test_validate_concurrency_exceeded(self) -> None:
        """Should reject excessive concurrency."""
        with pytest.raises(ValidationError, match="exceeds limit"):
            InputValidator.validate_concurrency(1000)

    def test_validate_concurrency_zero(self) -> None:
        """Should reject zero concurrency."""
        with pytest.raises(ValidationError, match="must be >= 1"):
            InputValidator.validate_concurrency(0)

    def test_validate_timeout_ok(self) -> None:
        """Should accept valid timeout."""
        InputValidator.validate_timeout(300)  # No exception

    def test_validate_timeout_negative(self) -> None:
        """Should reject negative timeout."""
        with pytest.raises(ValidationError, match="must be positive"):
            InputValidator.validate_timeout(-1)

    def test_validate_pagination_ok(self) -> None:
        """Should accept valid pagination."""
        InputValidator.validate_pagination(0, 20)  # No exception

    def test_validate_pagination_negative_skip(self) -> None:
        """Should reject negative skip."""
        with pytest.raises(ValidationError, match="skip must be >= 0"):
            InputValidator.validate_pagination(-1, 20)

    def test_validate_pagination_limit_zero(self) -> None:
        """Should reject zero limit."""
        with pytest.raises(ValidationError, match="limit must be >= 1"):
            InputValidator.validate_pagination(0, 0)

    def test_validate_workflow_definition_valid(self) -> None:
        """Should accept valid workflow definition."""
        workflow = {"tasks": {"t1": {}, "t2": {}}}
        InputValidator.validate_workflow_definition(workflow)  # No exception

    def test_validate_workflow_definition_missing_tasks(self) -> None:
        """Should reject workflow without tasks."""
        workflow = {"name": "test"}
        with pytest.raises(ValidationError, match="missing 'tasks'"):
            InputValidator.validate_workflow_definition(workflow)

    def test_validate_workflow_definition_invalid_task_id(self) -> None:
        """Should reject invalid task IDs."""
        workflow = {"tasks": {"t@invalid": {}}}
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_workflow_definition(workflow)


class TestRateLimiter:
    """Tests for rate limiting."""

    def test_rate_limiter_under_limit(self) -> None:
        """Should allow requests under limit."""
        limiter = RateLimiter(requests_per_minute=10)
        current_time = time.time()

        for i in range(10):
            assert limiter.is_allowed(current_time + i * 0.1) is True

    def test_rate_limiter_over_limit(self) -> None:
        """Should block requests over limit."""
        limiter = RateLimiter(requests_per_minute=5)
        current_time = time.time()

        for i in range(5):
            limiter.is_allowed(current_time + i * 0.1)

        assert limiter.is_allowed(current_time + 0.5) is False

    def test_rate_limiter_window_expiry(self) -> None:
        """Should reset after window expires."""
        limiter = RateLimiter(requests_per_minute=2)
        current_time = time.time()

        # Fill limit
        limiter.is_allowed(current_time)
        limiter.is_allowed(current_time + 0.1)

        # Should be blocked
        assert limiter.is_allowed(current_time + 0.2) is False

        # After window, should allow
        assert limiter.is_allowed(current_time + 61) is True


class TestSafetyLimits:
    """Tests for safety limit enforcement."""

    def test_enforce_request_size_ok(self) -> None:
        """Should accept request within limit."""
        SafetyLimits.enforce_request_size(1000000)  # 1 MB, under 10 MB limit

    def test_enforce_request_size_exceeded(self) -> None:
        """Should reject oversized request."""
        with pytest.raises(ValidationError, match="exceeds limit"):
            SafetyLimits.enforce_request_size(100 * 1024 * 1024)  # 100 MB

    def test_enforce_event_retention_ok(self) -> None:
        """Should accept events under limit."""
        assert SafetyLimits.enforce_event_retention(5000) is True

    def test_enforce_event_retention_exceeded(self) -> None:
        """Should block events over limit."""
        assert SafetyLimits.enforce_event_retention(50000) is False


class TestLifecycleManager:
    """Tests for lifecycle management."""

    @pytest.mark.asyncio
    async def test_lifecycle_initialization(self) -> None:
        """Should initialize lifecycle manager."""
        manager = LifecycleManager()

        assert manager.is_shutting_down is False
        assert manager.active_runs == 0
        assert manager.active_requests == 0

    def test_increment_decrement_runs(self) -> None:
        """Should track active runs."""
        manager = LifecycleManager()

        manager.increment_active_run()
        assert manager.active_runs == 1

        manager.increment_active_run()
        assert manager.active_runs == 2

        manager.decrement_active_run()
        assert manager.active_runs == 1

    def test_increment_decrement_requests(self) -> None:
        """Should track active requests."""
        manager = LifecycleManager()

        manager.increment_active_request()
        assert manager.active_requests == 1

        manager.decrement_active_request()
        assert manager.active_requests == 0

    def test_shutdown_status(self) -> None:
        """Should report shutdown status."""
        manager = LifecycleManager()
        manager.increment_active_run()
        manager.increment_active_request()

        status = manager.get_shutdown_status()

        assert status["is_shutting_down"] is False
        assert status["active_runs"] == 1
        assert status["active_requests"] == 1

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self) -> None:
        """Should execute graceful shutdown."""
        manager = LifecycleManager()
        callback_called = False

        def callback():
            nonlocal callback_called
            callback_called = True

        manager.register_shutdown_callback(callback)
        await manager.shutdown("TERM", graceful=True)

        assert manager.is_shutting_down is True
        assert callback_called is True

    @pytest.mark.asyncio
    async def test_startup_callbacks(self) -> None:
        """Should execute startup callbacks."""
        manager = LifecycleManager()
        startup_called = False

        def callback():
            nonlocal startup_called
            startup_called = True

        manager.register_startup_callback(callback)
        await manager.startup()

        assert startup_called is True

    @pytest.mark.asyncio
    async def test_shutdown_event_recording(self) -> None:
        """Should record shutdown events."""
        manager = LifecycleManager()
        manager.increment_active_run()

        await manager.shutdown("TERM")

        assert len(manager.shutdown_events) == 1
        event = manager.shutdown_events[0]
        assert event.signal_name == "TERM"
        assert event.active_runs == 1

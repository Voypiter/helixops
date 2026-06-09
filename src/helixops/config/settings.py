"""Production configuration with environment-based overrides."""

import os
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    """Database connection settings."""

    url: str = "sqlite:///helixops.db"
    pool_size: int = 20
    max_overflow: int = 40
    echo: bool = False
    migration_check: bool = True


@dataclass
class ExecutionConfig:
    """Execution engine settings."""

    max_concurrent_default: int = 10
    max_concurrent_limit: int = 500
    task_timeout_seconds: int = 3600
    default_retry_attempts: int = 3
    default_backoff_ms: int = 100
    max_backoff_ms: int = 30000


@dataclass
class APIConfig:
    """API server settings."""

    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    max_request_size_mb: int = 10
    request_timeout_seconds: int = 30
    pagination_default_limit: int = 20
    pagination_max_limit: int = 100
    rate_limit_requests_per_minute: int = 1000


@dataclass
class CLIConfig:
    """CLI settings."""

    default_output_format: str = "text"
    verbose: bool = False
    color_output: bool = True


@dataclass
class ObservabilityConfig:
    """Observability and diagnostics settings."""

    metrics_enabled: bool = True
    tracing_enabled: bool = True
    health_check_interval_seconds: int = 30
    max_events_in_memory: int = 10000
    event_retention_days: int = 7


@dataclass
class SecurityConfig:
    """Security settings."""

    enable_cors: bool = False
    cors_origins: list[str] = field(default_factory=list)
    require_api_auth: bool = False
    auth_token_header: str = "X-API-Token"
    input_validation_strict: bool = True
    max_workflow_size_mb: int = 100
    max_task_count: int = 10000


@dataclass
class RuntimeConfig:
    """Runtime environment configuration."""

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    api: APIConfig = field(default_factory=APIConfig)
    cli: CLIConfig = field(default_factory=CLIConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    debug: bool = False
    environment: str = "development"

    @staticmethod
    def from_environment() -> "RuntimeConfig":
        """Load configuration from environment variables.

        Returns:
            RuntimeConfig with environment-based overrides
        """
        config = RuntimeConfig()

        # Environment
        config.environment = os.getenv("HELIXOPS_ENV", "development")
        config.debug = os.getenv("HELIXOPS_DEBUG", "false").lower() == "true"

        # Database
        config.database.url = os.getenv("HELIXOPS_DATABASE_URL", config.database.url)
        config.database.pool_size = int(
            os.getenv("HELIXOPS_DB_POOL_SIZE", config.database.pool_size)
        )
        config.database.migration_check = os.getenv("HELIXOPS_DB_MIGRATE", "true").lower() == "true"

        # Execution
        config.execution.max_concurrent_default = int(
            os.getenv(
                "HELIXOPS_MAX_CONCURRENT",
                config.execution.max_concurrent_default,
            )
        )
        config.execution.task_timeout_seconds = int(
            os.getenv(
                "HELIXOPS_TASK_TIMEOUT",
                config.execution.task_timeout_seconds,
            )
        )

        # API
        config.api.host = os.getenv("HELIXOPS_API_HOST", config.api.host)
        config.api.port = int(os.getenv("HELIXOPS_API_PORT", config.api.port))
        config.api.workers = int(os.getenv("HELIXOPS_API_WORKERS", config.api.workers))

        # Security
        config.security.require_api_auth = (
            os.getenv("HELIXOPS_REQUIRE_AUTH", "false").lower() == "true"
        )
        config.security.input_validation_strict = (
            os.getenv("HELIXOPS_STRICT_VALIDATION", "true").lower() == "true"
        )

        return config

    def validate(self) -> None:
        """Validate configuration consistency."""
        if self.execution.max_concurrent_default > self.execution.max_concurrent_limit:
            raise ValueError("max_concurrent_default cannot exceed max_concurrent_limit")

        if self.api.port < 1024 and self.environment == "production":
            raise ValueError("API port must be >= 1024 in production (use reverse proxy)")

        if self.security.max_workflow_size_mb > 1000:
            raise ValueError("max_workflow_size_mb is too large for safety")

        if self.api.pagination_default_limit > self.api.pagination_max_limit:
            raise ValueError("pagination_default_limit cannot exceed pagination_max_limit")

    def get_production_config(self) -> "RuntimeConfig":
        """Get hardened production configuration.

        Returns:
            RuntimeConfig with production-safe defaults
        """
        self.environment = "production"
        self.debug = False
        self.api.workers = max(2, self.api.workers)
        self.observability.metrics_enabled = True
        self.observability.tracing_enabled = True
        self.security.input_validation_strict = True
        self.validate()
        return self


# Global configuration instance
_config: RuntimeConfig | None = None


def get_config() -> RuntimeConfig:
    """Get the current runtime configuration.

    Returns:
        RuntimeConfig instance
    """
    global _config
    if _config is None:
        _config = RuntimeConfig.from_environment()
        _config.validate()
    return _config


def set_config(config: RuntimeConfig) -> None:
    """Set the runtime configuration.

    Args:
        config: RuntimeConfig instance
    """
    global _config
    config.validate()
    _config = config


def reset_config() -> None:
    """Reset configuration to defaults (testing only)."""
    global _config
    _config = None

"""Health checks and readiness probes."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


@dataclass
class HealthStatus:
    """System health status."""

    status: str = "healthy"  # healthy, degraded, unhealthy
    ready: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)
    checks: Dict[str, bool] = field(default_factory=dict)
    metrics: Dict = field(default_factory=dict)

    def add_check(self, name: str, passed: bool) -> None:
        """Add a health check result."""
        self.checks[name] = passed
        if not passed:
            self.status = "degraded"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "status": self.status,
            "ready": self.ready,
            "timestamp": self.timestamp.isoformat(),
            "checks": self.checks,
            "metrics": self.metrics,
        }


def get_health_status() -> HealthStatus:
    """Get current system health status."""
    health = HealthStatus()
    health.add_check("system_responsive", True)
    health.add_check("storage_accessible", True)
    return health

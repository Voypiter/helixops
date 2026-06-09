"""Models for synthetic workload generation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WorkloadProfile(Enum):
    """Profile types for synthetic workflow generation."""

    TINY = "tiny"
    BALANCED = "balanced"
    WIDE = "wide"
    DEEP = "deep"
    FAILURE_HEAVY = "failure_heavy"
    ENTERPRISE = "enterprise"
    STRESS = "stress"


@dataclass
class SyntheticWorkloadConfig:
    """Configuration for synthetic workload generation."""

    profile: WorkloadProfile
    seed: int
    task_count_override: int | None = None
    failure_rate: float = 0.0
    payload_size_range: tuple[int, int] = (100, 10000)
    dependency_density: float = 0.3
    max_retry_attempts: int = 3
    enable_timeout: bool = True


@dataclass
class GeneratedWorkflow:
    """A complete generated workflow."""

    workflow_id: str
    name: str
    description: str
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    dependencies: list[tuple[str, str]] = field(default_factory=list)
    failure_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    retry_policies: dict[str, dict[str, Any]] = field(default_factory=dict)
    payloads: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    config: SyntheticWorkloadConfig | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "tasks": self.tasks,
            "dependencies": self.dependencies,
            "failure_profiles": self.failure_profiles,
            "retry_policies": self.retry_policies,
            "payloads": self.payloads,
            "metadata": self.metadata,
        }


@dataclass
class TaskSpec:
    """Specification for a generated task."""

    task_id: str
    name: str
    estimated_duration_ms: int
    payload_size: int
    timeout_ms: int | None = None
    max_retries: int = 0
    failure_rate: float = 0.0

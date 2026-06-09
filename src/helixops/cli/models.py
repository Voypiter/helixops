"""CLI output models and formatting."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OutputFormat(Enum):
    """Output format types."""

    TEXT = "text"
    JSON = "json"
    YAML = "yaml"


@dataclass
class CLIResult:
    """Standard CLI result wrapper."""

    success: bool
    data: Any = None
    message: str = ""
    exit_code: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class WorkflowInfo:
    """Display information about a workflow."""

    workflow_id: str
    name: str
    task_count: int
    dependency_count: int
    description: str = ""


@dataclass
class RunInfo:
    """Display information about a run."""

    run_id: str
    workflow_id: str
    state: str
    task_count: int
    succeeded_count: int
    failed_count: int
    duration_ms: int | None = None


@dataclass
class TaskInfo:
    """Display information about a task."""

    task_id: str
    task_name: str
    state: str
    attempt_number: int
    duration_ms: int | None = None
    error: str | None = None


@dataclass
class ValidationResult:
    """Validation result for a workflow."""

    is_valid: bool
    task_count: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

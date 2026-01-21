"""CLI output models and formatting."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


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
    errors: List[str] = None

    def __post_init__(self) -> None:
        """Initialize errors list if None."""
        if self.errors is None:
            self.errors = []


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
    duration_ms: Optional[int] = None


@dataclass
class TaskInfo:
    """Display information about a task."""

    task_id: str
    task_name: str
    state: str
    attempt_number: int
    duration_ms: Optional[int] = None
    error: Optional[str] = None


@dataclass
class ValidationResult:
    """Validation result for a workflow."""

    is_valid: bool
    task_count: int
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self) -> None:
        """Initialize lists if None."""
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

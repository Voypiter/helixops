"""Execution plan models for DAG planning."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskDependencyType(Enum):
    """Types of task dependencies."""

    DIRECT = "direct"  # Task must complete before dependent can start
    SOFT = "soft"  # Task should complete but dependent can proceed
    CONDITIONAL = "conditional"  # Dependency depends on outcome


@dataclass
class ExecutionWave:
    """A group of tasks that can execute concurrently."""

    wave_id: int
    task_ids: list[str] = field(default_factory=list)
    prerequisites: set[int] = field(default_factory=set)  # Wave IDs that must complete first

    def __post_init__(self) -> None:
        if self.wave_id < 0:
            raise ValueError(f"wave_id must be non-negative, got {self.wave_id}")
        if not self.task_ids:
            raise ValueError("ExecutionWave must contain at least one task")


@dataclass
class TaskDependencyInfo:
    """Information about a task's dependencies."""

    task_id: str
    direct_dependencies: set[str] = field(default_factory=set)
    transitive_dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)
    depth: int = 0  # Distance from root node
    width: int = 0  # Number of parallel tasks in deepest level


@dataclass
class ExecutionPlan:
    """A complete execution plan for a workflow."""

    workflow_id: str
    waves: list[ExecutionWave] = field(default_factory=list)
    task_ordering: list[str] = field(default_factory=list)  # Topological sort
    task_dependencies: dict[str, TaskDependencyInfo] = field(default_factory=dict)
    max_depth: int = 0
    critical_path_length: int = 0
    parallelism_factor: float = 0.0  # Avg tasks per wave
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_wave_for_task(self, task_id: str) -> int:
        """Get the wave ID for a task."""
        for wave in self.waves:
            if task_id in wave.task_ids:
                return wave.wave_id
        raise ValueError(f"Task {task_id} not found in execution plan")

    def get_tasks_in_wave(self, wave_id: int) -> list[str]:
        """Get all tasks in a specific wave."""
        for wave in self.waves:
            if wave.wave_id == wave_id:
                return wave.task_ids
        return []

    def get_predecessors(self, task_id: str) -> set[str]:
        """Get all tasks that must complete before this task."""
        if task_id not in self.task_dependencies:
            return set()
        return self.task_dependencies[task_id].direct_dependencies

    def get_successors(self, task_id: str) -> set[str]:
        """Get all tasks that depend on this task."""
        if task_id not in self.task_dependencies:
            return set()
        return self.task_dependencies[task_id].dependents


@dataclass
class GraphAnalysis:
    """Detailed analysis of workflow graph structure."""

    is_acyclic: bool = True
    has_cycles: list[list[str]] = field(default_factory=list)
    unreachable_tasks: set[str] = field(default_factory=set)
    orphan_tasks: set[str] = field(default_factory=set)  # Tasks with no path to root
    graph_depth: int = 0
    max_width: int = 0
    connected_components: list[set[str]] = field(default_factory=list)
    is_connected: bool = True
    critical_path: list[str] = field(default_factory=list)

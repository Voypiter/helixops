"""Deterministic DAG planning engine for workflow execution."""

from typing import Dict, List, Set, Optional
from collections import defaultdict, deque

from helixops.domain.models import Workflow
from helixops.domain.errors import (
    CyclicDependencyError,
    ValidationError,
)
from helixops.planning.models import (
    ExecutionPlan,
    ExecutionWave,
    TaskDependencyInfo,
    GraphAnalysis,
)


class DAGPlanningEngine:
    """Converts validated workflows into deterministic execution plans."""

    def __init__(self, workflow: Workflow):
        self.workflow = workflow
        self.graph = workflow.graph
        self.tasks = workflow.graph.tasks
        self._analysis: Optional[GraphAnalysis] = None

    def analyze_graph(self) -> GraphAnalysis:
        """Perform comprehensive graph analysis."""
        if self._analysis is not None:
            return self._analysis

        analysis = GraphAnalysis()
        cycles = self._detect_cycles()
        analysis.is_acyclic = len(cycles) == 0
        analysis.has_cycles = cycles
        analysis.unreachable_tasks = self._find_unreachable_tasks()
        analysis.orphan_tasks = self._find_orphan_tasks()
        components = self._find_connected_components()
        analysis.connected_components = components
        analysis.is_connected = len(components) == 1
        analysis.graph_depth = self._calculate_graph_depth()
        analysis.max_width = self._calculate_max_width()
        analysis.critical_path = self._find_critical_path()

        self._analysis = analysis
        return analysis

    def _detect_cycles(self) -> List[List[str]]:
        """Detect all cycles in the dependency graph."""
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(task_id: str) -> None:
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)

            task = self.tasks.get(task_id)
            if task:
                for dep_id in task.depends_on:
                    if dep_id not in visited:
                        dfs(dep_id)
                    elif dep_id in rec_stack:
                        cycle_start = path.index(dep_id)
                        cycle = path[cycle_start:] + [dep_id]
                        cycles.append(cycle)

            path.pop()
            rec_stack.remove(task_id)

        for task_id in self.tasks:
            if task_id not in visited:
                dfs(task_id)

        return cycles

    def _find_unreachable_tasks(self) -> Set[str]:
        """Find tasks that cannot be reached from any root task."""
        if not self.tasks:
            return set()

        reachable: Set[str] = set()
        for task_id in self.tasks:
            task = self.tasks[task_id]
            if not task.depends_on:
                reachable.add(task_id)
                reachable.update(self._get_reachable_from(task_id))

        return set(self.tasks.keys()) - reachable

    def _get_reachable_from(self, task_id: str) -> Set[str]:
        """Get all tasks reachable from a given task."""
        reachable: Set[str] = set()
        visited: Set[str] = set()
        queue = deque([task_id])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            for other_id, other_task in self.tasks.items():
                if current in other_task.depends_on and other_id not in visited:
                    reachable.add(other_id)
                    queue.append(other_id)

        return reachable

    def _find_orphan_tasks(self) -> Set[str]:
        """Find tasks that have no path to a root task."""
        orphans: Set[str] = set()
        for task_id in self.tasks:
            if not self._has_path_to_root(task_id):
                orphans.add(task_id)
        return orphans

    def _has_path_to_root(self, task_id: str) -> bool:
        """Check if task has a path to a root task."""
        visited: Set[str] = set()
        queue = deque([task_id])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            task = self.tasks.get(current)
            if task is None:
                continue

            if not task.depends_on:
                return True

            for dep_id in task.depends_on:
                if dep_id not in visited:
                    queue.append(dep_id)

        return False

    def _find_connected_components(self) -> List[Set[str]]:
        """Find all connected components in the graph."""
        visited: Set[str] = set()
        components: List[Set[str]] = []

        for task_id in self.tasks:
            if task_id not in visited:
                component = self._dfs_component(task_id, visited)
                components.append(component)

        return components

    def _dfs_component(self, task_id: str, visited: Set[str]) -> Set[str]:
        """Find all tasks in the same connected component."""
        component: Set[str] = set()
        stack = [task_id]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)

            task = self.tasks.get(current)
            if task:
                for dep_id in task.depends_on:
                    if dep_id not in visited:
                        stack.append(dep_id)

            for other_id, other_task in self.tasks.items():
                if current in other_task.depends_on and other_id not in visited:
                    stack.append(other_id)

        return component

    def _calculate_graph_depth(self) -> int:
        """Calculate the maximum depth of the dependency graph."""
        depths: Dict[str, int] = {}
        visiting: Set[str] = set()

        def get_depth(task_id: str) -> int:
            if task_id in depths:
                return depths[task_id]

            if task_id in visiting:
                return 0

            visiting.add(task_id)
            task = self.tasks.get(task_id)
            if not task or not task.depends_on:
                depths[task_id] = 0
                visiting.remove(task_id)
                return 0

            max_dep_depth = max(get_depth(dep_id) for dep_id in task.depends_on)
            depths[task_id] = max_dep_depth + 1
            visiting.remove(task_id)
            return depths[task_id]

        if not self.tasks:
            return 0

        return max(get_depth(task_id) for task_id in self.tasks)

    def _calculate_max_width(self) -> int:
        """Calculate the maximum width (concurrent tasks) at any depth."""
        task_depths: Dict[int, int] = defaultdict(int)
        depths_cache: Dict[str, int] = {}
        visiting: Set[str] = set()

        def get_depth(task_id: str) -> int:
            if task_id in depths_cache:
                return depths_cache[task_id]

            if task_id in visiting:
                return 0

            visiting.add(task_id)
            task = self.tasks.get(task_id)
            if not task or not task.depends_on:
                depths_cache[task_id] = 0
                visiting.remove(task_id)
                return 0

            max_dep_depth = max(get_depth(dep_id) for dep_id in task.depends_on)
            depths_cache[task_id] = max_dep_depth + 1
            visiting.remove(task_id)
            return depths_cache[task_id]

        for task_id in self.tasks:
            depth = get_depth(task_id)
            task_depths[depth] += 1

        return max(task_depths.values()) if task_depths else 0

    def _find_critical_path(self) -> List[str]:
        """Find the critical path (longest path from root to leaf)."""
        longest_paths: Dict[str, List[str]] = {}

        def find_longest(task_id: str) -> List[str]:
            if task_id in longest_paths:
                return longest_paths[task_id]

            task = self.tasks.get(task_id)
            if not task:
                return [task_id]

            dependents = [
                t_id for t_id, t in self.tasks.items() if task_id in t.depends_on
            ]

            if not dependents:
                longest_paths[task_id] = [task_id]
                return [task_id]

            longest = [task_id]
            for dep_id in dependents:
                candidate = [task_id] + find_longest(dep_id)
                if len(candidate) > len(longest):
                    longest = candidate

            longest_paths[task_id] = longest
            return longest

        if not self.tasks:
            return []

        roots = [t_id for t_id, t in self.tasks.items() if not t.depends_on]
        if not roots:
            return []

        critical = []
        for root_id in roots:
            path = find_longest(root_id)
            if len(path) > len(critical):
                critical = path

        return critical

    def plan(self) -> ExecutionPlan:
        """Generate an execution plan for the workflow."""
        self.workflow.validate()
        analysis = self.analyze_graph()

        if not analysis.is_acyclic:
            raise CyclicDependencyError(
                f"Workflow contains cycles: {analysis.has_cycles}"
            )

        if analysis.orphan_tasks:
            raise ValidationError(
                f"Workflow has orphan tasks: {analysis.orphan_tasks}"
            )

        if analysis.unreachable_tasks:
            raise ValidationError(
                f"Workflow has unreachable tasks: {analysis.unreachable_tasks}"
            )

        waves = self._calculate_waves()
        ordering = self._topological_sort()
        task_deps = self._build_dependency_info()

        plan = ExecutionPlan(
            workflow_id=self.workflow.workflow_id,
            waves=waves,
            task_ordering=ordering,
            task_dependencies=task_deps,
            max_depth=analysis.graph_depth,
            critical_path_length=len(analysis.critical_path),
            parallelism_factor=self._calculate_parallelism(waves),
        )

        return plan

    def _calculate_waves(self) -> List[ExecutionWave]:
        """Calculate execution waves for concurrent execution."""
        task_waves: Dict[str, int] = {}

        def get_wave(task_id: str) -> int:
            if task_id in task_waves:
                return task_waves[task_id]

            task = self.tasks.get(task_id)
            if not task or not task.depends_on:
                task_waves[task_id] = 0
                return 0

            max_dep_wave = max(get_wave(dep_id) for dep_id in task.depends_on)
            task_waves[task_id] = max_dep_wave + 1
            return task_waves[task_id]

        for task_id in self.tasks:
            get_wave(task_id)

        waves_dict: Dict[int, List[str]] = defaultdict(list)
        for task_id, wave_id in task_waves.items():
            waves_dict[wave_id].append(task_id)

        waves_list = []
        for wave_id in sorted(waves_dict.keys()):
            task_ids = sorted(waves_dict[wave_id])
            wave = ExecutionWave(wave_id=wave_id, task_ids=task_ids)
            waves_list.append(wave)

        for wave in waves_list:
            for task_id in wave.task_ids:
                task = self.tasks[task_id]
                for dep_id in task.depends_on:
                    dep_wave = task_waves[dep_id]
                    if dep_wave != wave.wave_id:
                        wave.prerequisites.add(dep_wave)

        return waves_list

    def _topological_sort(self) -> List[str]:
        """Generate deterministic topological ordering of tasks."""
        visited: Set[str] = set()
        order: List[str] = []

        def visit(task_id: str) -> None:
            if task_id in visited:
                return
            visited.add(task_id)

            task = self.tasks.get(task_id)
            if task:
                for dep_id in sorted(task.depends_on):
                    visit(dep_id)

            order.append(task_id)

        for task_id in sorted(self.tasks.keys()):
            visit(task_id)

        return order

    def _build_dependency_info(self) -> Dict[str, TaskDependencyInfo]:
        """Build detailed dependency information for each task."""
        info: Dict[str, TaskDependencyInfo] = {}

        for task_id, task in self.tasks.items():
            direct_deps = set(task.depends_on)
            transitive_deps = self._get_transitive_deps(task_id)
            dependents = self._get_dependents(task_id)
            depth = self._get_task_depth(task_id)

            info[task_id] = TaskDependencyInfo(
                task_id=task_id,
                direct_dependencies=direct_deps,
                transitive_dependencies=transitive_deps,
                dependents=dependents,
                depth=depth,
            )

        return info

    def _get_transitive_deps(self, task_id: str) -> Set[str]:
        """Get all transitive dependencies of a task."""
        visited: Set[str] = set()
        transitive: Set[str] = set()
        queue = deque([task_id])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            task = self.tasks.get(current)
            if task:
                for dep_id in task.depends_on:
                    transitive.add(dep_id)
                    queue.append(dep_id)

        return transitive

    def _get_dependents(self, task_id: str) -> Set[str]:
        """Get all tasks that depend on this task."""
        dependents: Set[str] = set()
        for other_id, other_task in self.tasks.items():
            if task_id in other_task.depends_on:
                dependents.add(other_id)
        return dependents

    def _get_task_depth(self, task_id: str) -> int:
        """Get the depth of a task in the dependency graph."""
        task = self.tasks.get(task_id)
        if not task or not task.depends_on:
            return 0
        return 1 + max(self._get_task_depth(dep_id) for dep_id in task.depends_on)

    def _calculate_parallelism(self, waves: List[ExecutionWave]) -> float:
        """Calculate average parallelism factor."""
        if not waves:
            return 0.0
        total_tasks = sum(len(wave.task_ids) for wave in waves)
        return total_tasks / len(waves)

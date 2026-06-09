"""Deterministic synthetic workflow generator."""

import random
from typing import Any
from uuid import uuid4

from helixops.generation.models import (
    GeneratedWorkflow,
    SyntheticWorkloadConfig,
    TaskSpec,
    WorkloadProfile,
)


class SyntheticWorkflowGenerator:
    """Generates deterministic synthetic workflows from seed and profile."""

    # Profile configurations: (min_tasks, max_tasks, avg_duration_ms, failure_rate, dependency_density)
    PROFILE_CONFIG = {
        WorkloadProfile.TINY: (2, 5, 100, 0.0, 0.2),
        WorkloadProfile.BALANCED: (10, 20, 200, 0.05, 0.4),
        WorkloadProfile.WIDE: (50, 100, 150, 0.0, 0.1),
        WorkloadProfile.DEEP: (50, 100, 100, 0.0, 0.9),
        WorkloadProfile.FAILURE_HEAVY: (10, 30, 200, 0.3, 0.5),
        WorkloadProfile.ENTERPRISE: (200, 300, 250, 0.1, 0.3),
        WorkloadProfile.STRESS: (1000, 1000, 50, 0.02, 0.05),
    }

    def __init__(self, config: SyntheticWorkloadConfig):
        """Initialize generator with configuration.

        Args:
            config: SyntheticWorkloadConfig with seed and profile
        """
        self.config = config
        self.rng = random.Random(config.seed)
        self.workflow_id = f"wf-{config.profile.value}-{config.seed}"

    def generate(self) -> GeneratedWorkflow:
        """Generate a complete synthetic workflow.

        Returns:
            GeneratedWorkflow with all components
        """
        # Generate tasks
        tasks = self._generate_tasks()
        task_ids = list(tasks.keys())

        # Generate dependencies
        dependencies = self._generate_dependencies(task_ids)

        # Generate failure profiles
        failure_profiles = self._generate_failure_profiles(task_ids)

        # Generate retry policies
        retry_policies = self._generate_retry_policies(task_ids)

        # Generate payloads
        payloads = self._generate_payloads(task_ids)

        # Create workflow
        profile_name = self.config.profile.value.upper()
        workflow = GeneratedWorkflow(
            workflow_id=self.workflow_id,
            name=f"Synthetic {profile_name} Workflow",
            description=f"Auto-generated {profile_name} workflow from seed {self.config.seed}",
            tasks={
                task_id: {"name": f"task-{task_id}", "spec": task}
                for task_id, task in tasks.items()
            },
            dependencies=dependencies,
            failure_profiles=failure_profiles,
            retry_policies=retry_policies,
            payloads=payloads,
            metadata={
                "profile": self.config.profile.value,
                "seed": self.config.seed,
                "task_count": len(task_ids),
                "dependency_count": len(dependencies),
                "avg_task_duration_ms": sum(t.estimated_duration_ms for t in tasks.values())
                // len(tasks),
            },
            config=self.config,
        )

        return workflow

    def _generate_tasks(self) -> dict[str, TaskSpec]:
        """Generate task specifications.

        Returns:
            Dictionary mapping task IDs to TaskSpec
        """
        min_tasks, max_tasks, avg_duration, _, _ = self.PROFILE_CONFIG[self.config.profile]

        task_count = self.config.task_count_override or self.rng.randint(min_tasks, max_tasks)
        tasks = {}

        for i in range(task_count):
            task_id = f"t{i:04d}"

            # Duration varies around average
            duration = max(50, int(avg_duration * self.rng.uniform(0.5, 1.5)))

            # Payload size
            min_size, max_size = self.config.payload_size_range
            payload_size = self.rng.randint(min_size, max_size)

            # Timeout if enabled
            timeout = int(duration * 2) if self.config.enable_timeout else None

            # Max retries based on profile
            max_retries = self.rng.randint(0, self.config.max_retry_attempts)

            # Failure rate
            failure_rate = min(self.config.failure_rate, self.rng.uniform(0, 0.3))

            tasks[task_id] = TaskSpec(
                task_id=task_id,
                name=f"Task {i}",
                estimated_duration_ms=duration,
                payload_size=payload_size,
                timeout_ms=timeout,
                max_retries=max_retries,
                failure_rate=failure_rate,
            )

        return tasks

    def _generate_dependencies(self, task_ids: list[str]) -> list[tuple[str, str]]:
        """Generate dependency structure.

        Args:
            task_ids: List of task identifiers

        Returns:
            List of (source, target) dependencies
        """
        _, _, _, _, dependency_density = self.PROFILE_CONFIG[self.config.profile]

        dependencies: list[tuple[str, str]] = []
        {tid: i for i, tid in enumerate(task_ids)}

        for i, _task_id in enumerate(task_ids):
            # Add a few dependencies to later tasks
            for j in range(i + 1, len(task_ids)):
                if self.rng.random() < dependency_density:
                    # Avoid creating cycles by only going forward
                    dependencies.append((task_ids[i], task_ids[j]))

        # Ensure at least one dependency for deeper profiles
        if not dependencies and len(task_ids) > 1:
            dependencies.append((task_ids[0], task_ids[1]))

        return dependencies

    def _generate_failure_profiles(self, task_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Generate failure profiles for tasks.

        Args:
            task_ids: List of task identifiers

        Returns:
            Dictionary mapping task IDs to failure profiles
        """
        failure_classes = ["TRANSIENT", "PERMANENT", "TIMEOUT"]
        profiles = {}

        for task_id in task_ids:
            failure_class = self.rng.choice(failure_classes)
            profiles[task_id] = {
                "failure_class": failure_class,
                "probability": self.rng.uniform(0, min(0.5, self.config.failure_rate)),
                "retryable": failure_class != "PERMANENT",
            }

        return profiles

    def _generate_retry_policies(self, task_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Generate retry policies for tasks.

        Args:
            task_ids: List of task identifiers

        Returns:
            Dictionary mapping task IDs to retry policies
        """
        policies = {}

        for task_id in task_ids:
            max_attempts = self.rng.randint(1, self.config.max_retry_attempts + 1)
            initial_backoff = self.rng.randint(100, 1000)

            policies[task_id] = {
                "max_attempts": max_attempts,
                "initial_backoff_ms": initial_backoff,
                "max_backoff_ms": initial_backoff * 100,
                "backoff_multiplier": self.rng.uniform(1.5, 3.0),
                "jitter_factor": self.rng.uniform(0.1, 0.5),
            }

        return policies

    def _generate_payloads(self, task_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Generate task payloads.

        Args:
            task_ids: List of task identifiers

        Returns:
            Dictionary mapping task IDs to payloads
        """
        payloads = {}

        for task_id in task_ids:
            payloads[task_id] = {
                "request_id": str(uuid4()),
                "task_seed": self.rng.randint(0, 1000000),
                "data_size_bytes": self.rng.randint(
                    self.config.payload_size_range[0],
                    self.config.payload_size_range[1],
                ),
                "operation": self.rng.choice(["compute", "fetch", "store", "transform"]),
            }

        return payloads


class EdgeCaseGenerator:
    """Generates edge-case graph structures for testing."""

    @staticmethod
    def diamond_pattern(seed: int = 42) -> GeneratedWorkflow:
        """Generate a diamond dependency pattern.

        Args:
            seed: Random seed

        Returns:
            Workflow with diamond pattern (A -> B,C -> D)
        """
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=seed,
            task_count_override=4,
        )

        gen = SyntheticWorkflowGenerator(config)
        workflow = gen.generate()

        # Override with diamond pattern
        task_ids = list(workflow.tasks.keys())
        if len(task_ids) >= 4:
            workflow.dependencies = [
                (task_ids[0], task_ids[1]),
                (task_ids[0], task_ids[2]),
                (task_ids[1], task_ids[3]),
                (task_ids[2], task_ids[3]),
            ]

        return workflow

    @staticmethod
    def chain_pattern(length: int = 10, seed: int = 42) -> GeneratedWorkflow:
        """Generate a linear chain dependency pattern.

        Args:
            length: Number of tasks in chain
            seed: Random seed

        Returns:
            Workflow with linear chain (A -> B -> C -> ...)
        """
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.DEEP,
            seed=seed,
            task_count_override=length,
        )

        gen = SyntheticWorkflowGenerator(config)
        workflow = gen.generate()

        # Override with chain
        task_ids = sorted(workflow.tasks.keys())
        workflow.dependencies = [(task_ids[i], task_ids[i + 1]) for i in range(len(task_ids) - 1)]

        return workflow

    @staticmethod
    def wide_pattern(width: int = 50, seed: int = 42) -> GeneratedWorkflow:
        """Generate a wide (parallel) dependency pattern.

        Args:
            width: Number of parallel tasks
            seed: Random seed

        Returns:
            Workflow with one task feeding to many (A -> B,C,D,...)
        """
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.WIDE,
            seed=seed,
            task_count_override=width + 1,
        )

        gen = SyntheticWorkflowGenerator(config)
        workflow = gen.generate()

        # Override with wide pattern
        task_ids = sorted(workflow.tasks.keys())
        workflow.dependencies = [(task_ids[0], task_ids[i]) for i in range(1, len(task_ids))]

        return workflow

    @staticmethod
    def single_task(seed: int = 42) -> GeneratedWorkflow:
        """Generate a workflow with a single task.

        Args:
            seed: Random seed

        Returns:
            Workflow with one task and no dependencies
        """
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.TINY,
            seed=seed,
            task_count_override=1,
        )

        gen = SyntheticWorkflowGenerator(config)
        return gen.generate()

    @staticmethod
    def disconnected_components(num_components: int = 3, seed: int = 42) -> GeneratedWorkflow:
        """Generate a workflow with disconnected components.

        Args:
            num_components: Number of independent components
            seed: Random seed

        Returns:
            Workflow with multiple disconnected subgraphs
        """
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=seed,
            task_count_override=num_components * 3,
        )

        gen = SyntheticWorkflowGenerator(config)
        workflow = gen.generate()

        # Override with disconnected components
        task_ids = sorted(workflow.tasks.keys())
        dependencies = []

        for component in range(num_components):
            start = component * 3
            if start + 2 < len(task_ids):
                # Create a small chain in each component
                dependencies.append((task_ids[start], task_ids[start + 1]))
                dependencies.append((task_ids[start + 1], task_ids[start + 2]))

        workflow.dependencies = dependencies
        return workflow

"""Benchmark and standard workload suites."""

from typing import Dict, List

from helixops.generation.generator import EdgeCaseGenerator, SyntheticWorkflowGenerator
from helixops.generation.models import GeneratedWorkflow, SyntheticWorkloadConfig, WorkloadProfile


class BenchmarkSuite:
    """Pre-configured benchmark workloads for testing and development."""

    @staticmethod
    def smoke_test() -> List[GeneratedWorkflow]:
        """Generate minimal test suite for quick smoke tests.

        Returns:
            List of workflows for smoke testing
        """
        return [
            EdgeCaseGenerator.single_task(seed=1001),
            EdgeCaseGenerator.chain_pattern(length=5, seed=1002),
            EdgeCaseGenerator.diamond_pattern(seed=1003),
        ]

    @staticmethod
    def regression_suite() -> List[GeneratedWorkflow]:
        """Generate workflows for regression testing.

        Returns:
            List of diverse workflows covering common patterns
        """
        workflows = []

        # Test each profile
        for profile in WorkloadProfile:
            config = SyntheticWorkloadConfig(
                profile=profile,
                seed=2000 + hash(profile.value) % 1000,
            )
            gen = SyntheticWorkflowGenerator(config)
            workflows.append(gen.generate())

        # Add edge cases
        workflows.extend([
            EdgeCaseGenerator.single_task(seed=2100),
            EdgeCaseGenerator.chain_pattern(length=10, seed=2101),
            EdgeCaseGenerator.diamond_pattern(seed=2102),
            EdgeCaseGenerator.wide_pattern(width=20, seed=2103),
            EdgeCaseGenerator.disconnected_components(num_components=2, seed=2104),
        ])

        return workflows

    @staticmethod
    def scalability_suite() -> List[GeneratedWorkflow]:
        """Generate workflows for scalability testing.

        Returns:
            List of increasingly large workflows
        """
        workflows = []

        # Small
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.TINY,
            seed=3001,
        )
        workflows.append(SyntheticWorkflowGenerator(config).generate())

        # Medium
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=3002,
        )
        workflows.append(SyntheticWorkflowGenerator(config).generate())

        # Large
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.ENTERPRISE,
            seed=3003,
        )
        workflows.append(SyntheticWorkflowGenerator(config).generate())

        # Extreme
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.STRESS,
            seed=3004,
        )
        workflows.append(SyntheticWorkflowGenerator(config).generate())

        return workflows

    @staticmethod
    def resilience_suite() -> List[GeneratedWorkflow]:
        """Generate workflows for resilience and recovery testing.

        Returns:
            List of failure-prone workflows
        """
        workflows = []

        # High failure rate
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.FAILURE_HEAVY,
            seed=4001,
            failure_rate=0.3,
        )
        workflows.append(SyntheticWorkflowGenerator(config).generate())

        # Moderate failures
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=4002,
            failure_rate=0.15,
        )
        workflows.append(SyntheticWorkflowGenerator(config).generate())

        # Recovery-heavy (deep chain with failures)
        workflows.append(EdgeCaseGenerator.chain_pattern(length=20, seed=4003))

        # Parallel failures (wide pattern)
        workflows.append(EdgeCaseGenerator.wide_pattern(width=30, seed=4004))

        return workflows

    @staticmethod
    def pathological_suite() -> List[GeneratedWorkflow]:
        """Generate pathological and edge-case workflows.

        Returns:
            List of unusual/extreme workflows
        """
        workflows = []

        # Very deep chain
        workflows.append(EdgeCaseGenerator.chain_pattern(length=100, seed=5001))

        # Very wide fan-out
        workflows.append(EdgeCaseGenerator.wide_pattern(width=100, seed=5002))

        # Complex diamond patterns
        for i in range(3):
            workflows.append(EdgeCaseGenerator.diamond_pattern(seed=5010 + i))

        # Disconnected components
        for num_comp in [2, 5, 10]:
            workflows.append(
                EdgeCaseGenerator.disconnected_components(num_components=num_comp, seed=5020 + num_comp)
            )

        # Single task
        workflows.append(EdgeCaseGenerator.single_task(seed=5030))

        return workflows


class WorkloadLibrary:
    """Standard workloads for common scenarios."""

    @staticmethod
    def get_all_benchmarks() -> Dict[str, List[GeneratedWorkflow]]:
        """Get all benchmark suites.

        Returns:
            Dictionary mapping suite names to workflow lists
        """
        return {
            "smoke": BenchmarkSuite.smoke_test(),
            "regression": BenchmarkSuite.regression_suite(),
            "scalability": BenchmarkSuite.scalability_suite(),
            "resilience": BenchmarkSuite.resilience_suite(),
            "pathological": BenchmarkSuite.pathological_suite(),
        }

    @staticmethod
    def generate_by_name(suite_name: str, index: int = 0) -> GeneratedWorkflow:
        """Generate a workflow by suite and index.

        Args:
            suite_name: Name of benchmark suite
            index: Index within suite

        Returns:
            Generated workflow

        Raises:
            ValueError: If suite or index not found
        """
        benchmarks = WorkloadLibrary.get_all_benchmarks()
        if suite_name not in benchmarks:
            raise ValueError(f"Unknown benchmark suite: {suite_name}")

        suite = benchmarks[suite_name]
        if index >= len(suite):
            raise ValueError(f"Index {index} out of range for suite {suite_name} (max {len(suite)})")

        return suite[index]

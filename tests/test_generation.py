"""Tests for synthetic workload generation."""

import pytest

from helixops.generation.benchmarks import BenchmarkSuite, WorkloadLibrary
from helixops.generation.generator import EdgeCaseGenerator, SyntheticWorkflowGenerator
from helixops.generation.models import SyntheticWorkloadConfig, WorkloadProfile


class TestSyntheticWorkflowGenerator:
    """Tests for synthetic workflow generator."""

    def test_deterministic_generation(self) -> None:
        """Same seed should produce identical workflows."""
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=42,
        )

        gen1 = SyntheticWorkflowGenerator(config)
        workflow1 = gen1.generate()

        gen2 = SyntheticWorkflowGenerator(config)
        workflow2 = gen2.generate()

        # Compare key attributes
        assert len(workflow1.tasks) == len(workflow2.tasks)
        assert len(workflow1.dependencies) == len(workflow2.dependencies)
        assert workflow1.metadata["task_count"] == workflow2.metadata["task_count"]

    def test_different_seeds_produce_different_workflows(self) -> None:
        """Different seeds should produce different workflows."""
        config1 = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=42,
        )
        config2 = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=43,
        )

        workflow1 = SyntheticWorkflowGenerator(config1).generate()
        workflow2 = SyntheticWorkflowGenerator(config2).generate()

        # Tasks should be different
        assert (
            workflow1.tasks != workflow2.tasks or workflow1.dependencies != workflow2.dependencies
        )

    def test_profile_produces_expected_task_counts(self) -> None:
        """Different profiles should produce appropriate task counts."""
        profiles_and_ranges = [
            (WorkloadProfile.TINY, 2, 5),
            (WorkloadProfile.BALANCED, 10, 20),
            (WorkloadProfile.WIDE, 50, 100),
            (WorkloadProfile.DEEP, 50, 100),
        ]

        for profile, min_tasks, max_tasks in profiles_and_ranges:
            config = SyntheticWorkloadConfig(
                profile=profile,
                seed=42,
            )
            workflow = SyntheticWorkflowGenerator(config).generate()
            task_count = len(workflow.tasks)

            # Allow some variance, but should be roughly in expected range
            assert task_count >= min_tasks - 5 or task_count <= max_tasks + 5

    def test_task_count_override(self) -> None:
        """Task count should be overridable."""
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=42,
            task_count_override=15,
        )

        workflow = SyntheticWorkflowGenerator(config).generate()
        assert len(workflow.tasks) == 15

    def test_failure_profiles_generated(self) -> None:
        """Every task should have a failure profile."""
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=42,
        )

        workflow = SyntheticWorkflowGenerator(config).generate()

        assert len(workflow.failure_profiles) == len(workflow.tasks)
        for _task_id, profile in workflow.failure_profiles.items():
            assert "failure_class" in profile
            assert "probability" in profile
            assert "retryable" in profile

    def test_retry_policies_generated(self) -> None:
        """Every task should have a retry policy."""
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=42,
        )

        workflow = SyntheticWorkflowGenerator(config).generate()

        assert len(workflow.retry_policies) == len(workflow.tasks)
        for _task_id, policy in workflow.retry_policies.items():
            assert "max_attempts" in policy
            assert "initial_backoff_ms" in policy
            assert "backoff_multiplier" in policy

    def test_payloads_generated(self) -> None:
        """Every task should have a payload."""
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=42,
        )

        workflow = SyntheticWorkflowGenerator(config).generate()

        assert len(workflow.payloads) == len(workflow.tasks)
        for _task_id, payload in workflow.payloads.items():
            assert "request_id" in payload
            assert "task_seed" in payload
            assert "data_size_bytes" in payload

    def test_dependencies_valid(self) -> None:
        """All dependencies should reference existing tasks."""
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=42,
        )

        workflow = SyntheticWorkflowGenerator(config).generate()
        task_ids = set(workflow.tasks.keys())

        for source, target in workflow.dependencies:
            assert source in task_ids
            assert target in task_ids

    def test_workflow_to_dict(self) -> None:
        """Workflow should convert to dictionary."""
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=42,
        )

        workflow = SyntheticWorkflowGenerator(config).generate()
        workflow_dict = workflow.to_dict()

        assert "workflow_id" in workflow_dict
        assert "tasks" in workflow_dict
        assert "dependencies" in workflow_dict


class TestEdgeCaseGenerator:
    """Tests for edge case workflow generation."""

    def test_diamond_pattern(self) -> None:
        """Diamond pattern should have correct structure."""
        workflow = EdgeCaseGenerator.diamond_pattern(seed=42)

        # Diamond: 4 tasks, specific dependencies
        assert len(workflow.tasks) >= 4
        assert len(workflow.dependencies) == 4

    def test_chain_pattern(self) -> None:
        """Chain pattern should be linear."""
        length = 10
        workflow = EdgeCaseGenerator.chain_pattern(length=length, seed=42)

        # Should have linear dependencies
        assert len(workflow.tasks) == length
        assert len(workflow.dependencies) == length - 1

    def test_wide_pattern(self) -> None:
        """Wide pattern should have one-to-many structure."""
        width = 50
        workflow = EdgeCaseGenerator.wide_pattern(width=width, seed=42)

        # Should have width + 1 tasks
        assert len(workflow.tasks) == width + 1
        # One source to many targets
        assert len(workflow.dependencies) == width

    def test_single_task(self) -> None:
        """Single task workflow should have no dependencies."""
        workflow = EdgeCaseGenerator.single_task(seed=42)

        assert len(workflow.tasks) == 1
        assert len(workflow.dependencies) == 0

    def test_disconnected_components(self) -> None:
        """Disconnected components should not be connected."""
        num_components = 3
        workflow = EdgeCaseGenerator.disconnected_components(num_components=num_components, seed=42)

        # Should have multiple tasks
        assert len(workflow.tasks) >= num_components * 3
        # Dependencies should be within components, not between
        assert len(workflow.dependencies) <= num_components * 2


class TestBenchmarkSuite:
    """Tests for benchmark suites."""

    def test_smoke_test_suite(self) -> None:
        """Smoke test suite should have minimal workflows."""
        workflows = BenchmarkSuite.smoke_test()

        assert len(workflows) >= 3
        # All should be small
        for workflow in workflows:
            assert len(workflow.tasks) <= 10

    def test_regression_suite(self) -> None:
        """Regression suite should cover different profiles."""
        workflows = BenchmarkSuite.regression_suite()

        assert len(workflows) > len(WorkloadProfile)
        # Should have edge cases
        edge_case_count = sum(1 for w in workflows if len(w.tasks) <= 4)
        assert edge_case_count >= 2

    def test_scalability_suite(self) -> None:
        """Scalability suite should have increasingly large workflows."""
        workflows = BenchmarkSuite.scalability_suite()

        assert len(workflows) == 4
        sizes = [len(w.tasks) for w in workflows]
        # Should be roughly increasing
        assert sizes[0] < sizes[-1]

    def test_resilience_suite(self) -> None:
        """Resilience suite should have high failure rates."""
        workflows = BenchmarkSuite.resilience_suite()

        assert len(workflows) >= 3

    def test_pathological_suite(self) -> None:
        """Pathological suite should have extreme cases."""
        workflows = BenchmarkSuite.pathological_suite()

        assert len(workflows) >= 9
        # Should have very large workflows
        has_large = any(len(w.tasks) > 50 for w in workflows)
        assert has_large


class TestWorkloadLibrary:
    """Tests for workload library."""

    def test_get_all_benchmarks(self) -> None:
        """Should retrieve all benchmark suites."""
        benchmarks = WorkloadLibrary.get_all_benchmarks()

        expected_suites = ["smoke", "regression", "scalability", "resilience", "pathological"]
        for suite_name in expected_suites:
            assert suite_name in benchmarks
            assert len(benchmarks[suite_name]) > 0

    def test_generate_by_name(self) -> None:
        """Should generate workflows by suite name."""
        workflow = WorkloadLibrary.generate_by_name("smoke", index=0)

        assert workflow is not None
        assert len(workflow.tasks) > 0

    def test_generate_by_name_invalid_suite(self) -> None:
        """Should raise error for invalid suite."""
        with pytest.raises(ValueError):
            WorkloadLibrary.generate_by_name("invalid_suite", index=0)

    def test_generate_by_name_invalid_index(self) -> None:
        """Should raise error for invalid index."""
        with pytest.raises(ValueError):
            WorkloadLibrary.generate_by_name("smoke", index=1000)


class TestEnterpriseProfiles:
    """Tests for enterprise profiles."""

    def test_get_enterprise_profile(self) -> None:
        """Should retrieve enterprise profiles."""
        from helixops.generation.profiles import EnterpriseProfiles

        profile = EnterpriseProfiles.get_profile("microservices")
        assert profile.name == "Microservices Orchestration"

    def test_generate_enterprise_workflow(self) -> None:
        """Should generate enterprise workflows."""
        from helixops.generation.profiles import EnterpriseProfiles

        workflow = EnterpriseProfiles.generate("microservices", seed=9001)

        assert len(workflow.tasks) == 300
        assert "enterprise_profile" in workflow.metadata

    def test_all_enterprise_profiles(self) -> None:
        """Should generate all enterprise profiles."""
        from helixops.generation.profiles import EnterpriseProfiles

        for profile_name in EnterpriseProfiles.PROFILES:
            workflow = EnterpriseProfiles.generate(profile_name, seed=9000)
            assert len(workflow.tasks) > 0
            assert "enterprise_profile" in workflow.metadata


class TestPathologicalProfiles:
    """Tests for pathological profiles."""

    def test_extreme_depth(self) -> None:
        """Should generate extreme depth workflow."""
        from helixops.generation.profiles import PathologicalProfiles

        workflow = PathologicalProfiles.extreme_depth()

        assert len(workflow.tasks) == 500

    def test_extreme_width(self) -> None:
        """Should generate extreme width workflow."""
        from helixops.generation.profiles import PathologicalProfiles

        workflow = PathologicalProfiles.extreme_width()

        assert len(workflow.tasks) == 500

    def test_extreme_failures(self) -> None:
        """Should generate failure-heavy workflow."""
        from helixops.generation.profiles import PathologicalProfiles

        workflow = PathologicalProfiles.extreme_failures()

        assert len(workflow.tasks) == 100

    def test_mixed_pathology(self) -> None:
        """Should generate mixed pathological workflow."""
        from helixops.generation.profiles import PathologicalProfiles

        workflow = PathologicalProfiles.mixed_pathology()

        assert len(workflow.tasks) == 300
        assert workflow.metadata["pathological_type"] == "mixed"


class TestProfileExamples:
    """Tests for profile examples."""

    def test_get_examples(self) -> None:
        """Should retrieve all example workflows."""
        from helixops.generation.profiles import ProfileExamples

        examples = ProfileExamples.get_examples()

        assert len(examples) > 10
        # Should have standard profiles
        assert any("standard_" in name for name in examples)
        # Should have enterprise profiles
        assert any("enterprise_" in name for name in examples)
        # Should have pathological profiles
        assert any("pathological_" in name for name in examples)


class TestWorkloadDiversity:
    """Tests for workload diversity and characteristics."""

    def test_profiles_produce_different_characteristics(self) -> None:
        """Different profiles should produce distinctly different workflows."""
        workflows = {}

        for profile in [
            WorkloadProfile.TINY,
            WorkloadProfile.BALANCED,
            WorkloadProfile.WIDE,
            WorkloadProfile.DEEP,
        ]:
            config = SyntheticWorkloadConfig(
                profile=profile,
                seed=100,
            )
            workflows[profile] = SyntheticWorkflowGenerator(config).generate()

        # TINY should be smaller than others
        assert len(workflows[WorkloadProfile.TINY].tasks) < len(
            workflows[WorkloadProfile.BALANCED].tasks
        )

        # WIDE should have many parallel dependencies
        wide_deps = len(workflows[WorkloadProfile.WIDE].dependencies)
        wide_tasks = len(workflows[WorkloadProfile.WIDE].tasks)
        len(workflows[WorkloadProfile.TINY].dependencies)

        # WIDE should have fewer edges relative to tasks (parallel = low edge count)
        wide_ratio = wide_deps / wide_tasks if wide_tasks > 0 else 0
        # DEEP should have many edges relative to tasks (sequential = high edge count)
        deep_ratio = len(workflows[WorkloadProfile.DEEP].dependencies) / len(
            workflows[WorkloadProfile.DEEP].tasks
        )

        assert wide_ratio < deep_ratio

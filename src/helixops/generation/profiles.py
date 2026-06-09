"""Specialized workload profiles for enterprise and pathological scenarios."""

from dataclasses import dataclass

from helixops.generation.generator import SyntheticWorkflowGenerator
from helixops.generation.models import GeneratedWorkflow, SyntheticWorkloadConfig, WorkloadProfile


@dataclass
class EnterpriseProfile:
    """Enterprise workload profile with realistic characteristics."""

    name: str
    description: str
    task_count: int
    failure_rate: float
    avg_task_duration_ms: int
    dependency_density: float
    payload_size_range: tuple[int, int]


class EnterpriseProfiles:
    """Standard enterprise workload profiles."""

    PROFILES = {
        "microservices": EnterpriseProfile(
            name="Microservices Orchestration",
            description="Typical microservice deployment workflow with 300+ tasks",
            task_count=300,
            failure_rate=0.08,
            avg_task_duration_ms=250,
            dependency_density=0.25,
            payload_size_range=(500, 50000),
        ),
        "data_pipeline": EnterpriseProfile(
            name="Data Processing Pipeline",
            description="Complex data pipeline with high parallelism (200 tasks)",
            task_count=200,
            failure_rate=0.05,
            avg_task_duration_ms=300,
            dependency_density=0.15,
            payload_size_range=(10000, 100000),
        ),
        "ci_cd": EnterpriseProfile(
            name="CI/CD Build Pipeline",
            description="Continuous integration with multiple stages (250 tasks)",
            task_count=250,
            failure_rate=0.12,
            avg_task_duration_ms=200,
            dependency_density=0.35,
            payload_size_range=(1000, 20000),
        ),
        "analytics": EnterpriseProfile(
            name="Analytics Computation",
            description="Distributed analytics with aggregation (400+ tasks)",
            task_count=400,
            failure_rate=0.06,
            avg_task_duration_ms=500,
            dependency_density=0.1,
            payload_size_range=(5000, 500000),
        ),
    }

    @staticmethod
    def get_profile(name: str) -> EnterpriseProfile:
        """Get enterprise profile by name.

        Args:
            name: Profile name

        Returns:
            EnterpriseProfile instance

        Raises:
            ValueError: If profile not found
        """
        if name not in EnterpriseProfiles.PROFILES:
            raise ValueError(f"Unknown enterprise profile: {name}")
        return EnterpriseProfiles.PROFILES[name]

    @staticmethod
    def generate(profile_name: str, seed: int) -> GeneratedWorkflow:
        """Generate a workflow from enterprise profile.

        Args:
            profile_name: Profile name (e.g., 'microservices')
            seed: Random seed

        Returns:
            Generated workflow
        """
        profile = EnterpriseProfiles.get_profile(profile_name)

        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.ENTERPRISE,
            seed=seed,
            task_count_override=profile.task_count,
            failure_rate=profile.failure_rate,
            payload_size_range=profile.payload_size_range,
            dependency_density=profile.dependency_density,
        )

        gen = SyntheticWorkflowGenerator(config)
        workflow = gen.generate()
        workflow.metadata["enterprise_profile"] = profile_name
        workflow.metadata["profile_description"] = profile.description
        workflow.name = f"Enterprise {profile.name}"
        workflow.description = profile.description

        return workflow


class PathologicalProfiles:
    """Pathological and adversarial workload profiles for stress testing."""

    @staticmethod
    def extreme_depth(seed: int = 6001) -> GeneratedWorkflow:
        """Generate extremely deep sequential workflow (500+ tasks in chain).

        Args:
            seed: Random seed

        Returns:
            Pathological deep workflow
        """
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.DEEP,
            seed=seed,
            task_count_override=500,
            dependency_density=0.95,
        )

        gen = SyntheticWorkflowGenerator(config)
        return gen.generate()

    @staticmethod
    def extreme_width(seed: int = 6002) -> GeneratedWorkflow:
        """Generate extremely wide parallel workflow (500+ parallel tasks).

        Args:
            seed: Random seed

        Returns:
            Pathological wide workflow
        """
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.WIDE,
            seed=seed,
            task_count_override=500,
            dependency_density=0.05,
        )

        gen = SyntheticWorkflowGenerator(config)
        return gen.generate()

    @staticmethod
    def extreme_failures(seed: int = 6003) -> GeneratedWorkflow:
        """Generate high-failure workflow (50% failure rate).

        Args:
            seed: Random seed

        Returns:
            Failure-heavy workflow
        """
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.FAILURE_HEAVY,
            seed=seed,
            task_count_override=100,
            failure_rate=0.5,
        )

        gen = SyntheticWorkflowGenerator(config)
        return gen.generate()

    @staticmethod
    def extreme_stress(seed: int = 6004) -> GeneratedWorkflow:
        """Generate extreme stress test (5000+ tasks).

        Args:
            seed: Random seed

        Returns:
            Extreme scale workflow
        """
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.STRESS,
            seed=seed,
            task_count_override=5000,
        )

        gen = SyntheticWorkflowGenerator(config)
        return gen.generate()

    @staticmethod
    def mixed_pathology(seed: int = 6005) -> GeneratedWorkflow:
        """Generate mixed pathological workflow (deep + wide + failures).

        Args:
            seed: Random seed

        Returns:
            Complex pathological workflow
        """
        config = SyntheticWorkloadConfig(
            profile=WorkloadProfile.BALANCED,
            seed=seed,
            task_count_override=300,
            failure_rate=0.25,
            dependency_density=0.4,
        )

        gen = SyntheticWorkflowGenerator(config)
        workflow = gen.generate()
        workflow.metadata["pathological_type"] = "mixed"
        return workflow


class ProfileExamples:
    """Example workflows demonstrating different profiles."""

    @staticmethod
    def get_examples() -> dict[str, GeneratedWorkflow]:
        """Get a collection of example workflows.

        Returns:
            Dictionary mapping profile names to example workflows
        """
        examples = {}

        # Standard profiles
        for profile in WorkloadProfile:
            config = SyntheticWorkloadConfig(
                profile=profile,
                seed=7000 + hash(profile.value) % 1000,
            )
            gen = SyntheticWorkflowGenerator(config)
            examples[f"standard_{profile.value}"] = gen.generate()

        # Enterprise profiles
        for name in EnterpriseProfiles.PROFILES:
            examples[f"enterprise_{name}"] = EnterpriseProfiles.generate(name, seed=8000)

        # Pathological profiles
        examples["pathological_extreme_depth"] = PathologicalProfiles.extreme_depth()
        examples["pathological_extreme_width"] = PathologicalProfiles.extreme_width()
        examples["pathological_extreme_failures"] = PathologicalProfiles.extreme_failures()
        examples["pathological_mixed"] = PathologicalProfiles.mixed_pathology()

        return examples

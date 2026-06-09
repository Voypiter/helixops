"""HelixOps CLI application."""

import json
from pathlib import Path

import typer

from helixops.cli.models import (
    OutputFormat,
)
from helixops.generation.benchmarks import WorkloadLibrary
from helixops.generation.generator import SyntheticWorkflowGenerator
from helixops.generation.models import SyntheticWorkloadConfig, WorkloadProfile
from helixops.generation.profiles import EnterpriseProfiles, PathologicalProfiles

app = typer.Typer(help="HelixOps: Workflow orchestration and execution engine")


@app.command()
def generate(
    profile: WorkloadProfile = typer.Option(
        WorkloadProfile.BALANCED,
        help="Workflow profile type",
    ),
    seed: int = typer.Option(
        42,
        help="Random seed for deterministic generation",
    ),
    task_count: int | None = typer.Option(
        None,
        help="Override task count",
    ),
    output: Path | None = typer.Option(
        None,
        help="Output file (defaults to stdout)",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.JSON,
        help="Output format",
    ),
) -> None:
    """Generate a synthetic workflow."""
    try:
        config = SyntheticWorkloadConfig(
            profile=profile,
            seed=seed,
            task_count_override=task_count,
        )

        gen = SyntheticWorkflowGenerator(config)
        workflow = gen.generate()

        output_data = workflow.to_dict() if format == OutputFormat.JSON else workflow

        if format == OutputFormat.JSON:
            output_text = json.dumps(output_data, indent=2, default=str)
        else:
            output_text = f"Generated workflow: {workflow.name}\nTasks: {len(workflow.tasks)}\nDependencies: {len(workflow.dependencies)}"

        if output:
            output.write_text(output_text)
            typer.echo(f"✓ Workflow saved to {output}")
        else:
            typer.echo(output_text)

    except Exception as e:
        typer.echo(f"✗ Error generating workflow: {str(e)}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def validate(
    workflow: Path = typer.Argument(
        ...,
        help="Workflow file path",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.TEXT,
        help="Output format",
    ),
) -> None:
    """Validate a workflow definition."""
    try:
        if not workflow.exists():
            typer.echo(f"✗ File not found: {workflow}", err=True)
            raise typer.Exit(code=1)

        workflow_data = json.loads(workflow.read_text())

        # Basic validation
        errors: list[str] = []
        warnings: list[str] = []

        if "tasks" not in workflow_data:
            errors.append("Missing 'tasks' field")
        else:
            task_count = len(workflow_data["tasks"])
            if task_count == 0:
                errors.append("No tasks defined")

        is_valid = len(errors) == 0

        if format == OutputFormat.JSON:
            result = {
                "valid": is_valid,
                "task_count": len(workflow_data.get("tasks", [])),
                "errors": errors,
                "warnings": warnings,
            }
            typer.echo(json.dumps(result, indent=2))
        else:
            status = "✓ VALID" if is_valid else "✗ INVALID"
            typer.echo(f"{status}")
            typer.echo(f"Tasks: {len(workflow_data.get('tasks', []))}")
            if errors:
                typer.echo("Errors:")
                for error in errors:
                    typer.echo(f"  - {error}")
            if warnings:
                typer.echo("Warnings:")
                for warning in warnings:
                    typer.echo(f"  - {warning}")

        if not is_valid:
            raise typer.Exit(code=1)

    except json.JSONDecodeError as e:
        typer.echo(f"✗ Invalid JSON in {workflow}", err=True)
        raise typer.Exit(code=1) from e
    except Exception as e:
        typer.echo(f"✗ Error validating workflow: {str(e)}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def benchmark(
    suite: str = typer.Option(
        "smoke",
        help="Benchmark suite name (smoke, regression, scalability, resilience, pathological)",
    ),
    index: int | None = typer.Option(
        None,
        help="Specific test index in suite",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.TEXT,
        help="Output format",
    ),
) -> None:
    """Run benchmark scenarios."""
    try:
        try:
            if index is not None:
                workflow = WorkloadLibrary.generate_by_name(suite, index)
            else:
                benchmarks = WorkloadLibrary.get_all_benchmarks()
                if suite not in benchmarks:
                    raise ValueError(f"Unknown suite: {suite}")
                workflows = benchmarks[suite]
                workflow = workflows[0] if workflows else None  # type: ignore[assignment]

                if not workflow:
                    typer.echo(f"✗ No workflows in suite: {suite}", err=True)
                    raise typer.Exit(code=1)

                if format == OutputFormat.JSON:
                    suite_data = {
                        "suite": suite,
                        "count": len(workflows),
                        "workflows": [
                            {
                                "id": w.workflow_id,
                                "tasks": len(w.tasks),
                                "dependencies": len(w.dependencies),
                            }
                            for w in workflows
                        ],
                    }
                    typer.echo(json.dumps(suite_data, indent=2))
                else:
                    typer.echo(f"Benchmark Suite: {suite}")
                    typer.echo(f"Total workflows: {len(workflows)}")
                    for i, w in enumerate(workflows):
                        typer.echo(f"  [{i}] {w.workflow_id}: {len(w.tasks)} tasks")
                return

        except ValueError as e:
            typer.echo(f"✗ {str(e)}", err=True)
            raise typer.Exit(code=1) from e

        if format == OutputFormat.JSON:
            workflow_data = workflow.to_dict()
            typer.echo(json.dumps(workflow_data, indent=2, default=str))
        else:
            typer.echo(f"Workflow: {workflow.name}")
            typer.echo(f"Tasks: {len(workflow.tasks)}")
            typer.echo(f"Dependencies: {len(workflow.dependencies)}")
            typer.echo(f"Description: {workflow.description}")

    except Exception as e:
        typer.echo(f"✗ Error running benchmark: {str(e)}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def enterprise(
    profile: str = typer.Option(
        "microservices",
        help="Enterprise profile (microservices, data_pipeline, ci_cd, analytics)",
    ),
    seed: int = typer.Option(
        8000,
        help="Random seed",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.TEXT,
        help="Output format",
    ),
) -> None:
    """Generate enterprise workload profile."""
    try:
        workflow = EnterpriseProfiles.generate(profile, seed=seed)

        if format == OutputFormat.JSON:
            workflow_data = workflow.to_dict()
            typer.echo(json.dumps(workflow_data, indent=2, default=str))
        else:
            typer.echo(f"Enterprise Workflow: {workflow.name}")
            typer.echo(f"Description: {workflow.description}")
            typer.echo(f"Tasks: {len(workflow.tasks)}")
            typer.echo(f"Dependencies: {len(workflow.dependencies)}")

    except ValueError as e:
        typer.echo(f"✗ Unknown enterprise profile: {profile}", err=True)
        raise typer.Exit(code=1) from e
    except Exception as e:
        typer.echo(f"✗ Error generating enterprise workflow: {str(e)}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def pathological(
    case: str = typer.Option(
        "extreme_depth",
        help="Pathological case (extreme_depth, extreme_width, extreme_failures, mixed)",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.TEXT,
        help="Output format",
    ),
) -> None:
    """Generate pathological test case."""
    try:
        case_map = {
            "extreme_depth": PathologicalProfiles.extreme_depth,
            "extreme_width": PathologicalProfiles.extreme_width,
            "extreme_failures": PathologicalProfiles.extreme_failures,
            "mixed": PathologicalProfiles.mixed_pathology,
        }

        if case not in case_map:
            typer.echo(f"✗ Unknown pathological case: {case}", err=True)
            raise typer.Exit(code=1)

        workflow = case_map[case]()

        if format == OutputFormat.JSON:
            workflow_data = workflow.to_dict()
            typer.echo(json.dumps(workflow_data, indent=2, default=str))
        else:
            typer.echo(f"Pathological Case: {case}")
            typer.echo(f"Workflow ID: {workflow.workflow_id}")
            typer.echo(f"Tasks: {len(workflow.tasks)}")
            typer.echo(f"Dependencies: {len(workflow.dependencies)}")
            if "pathological_type" in workflow.metadata:
                typer.echo(f"Type: {workflow.metadata['pathological_type']}")

    except Exception as e:
        typer.echo(f"✗ Error generating pathological case: {str(e)}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def list_suites(
    format: OutputFormat = typer.Option(
        OutputFormat.TEXT,
        help="Output format",
    ),
) -> None:
    """List available benchmark suites."""
    try:
        benchmarks = WorkloadLibrary.get_all_benchmarks()

        if format == OutputFormat.JSON:
            suite_data = {
                "suites": {
                    name: {"count": len(workflows)} for name, workflows in benchmarks.items()
                }
            }
            typer.echo(json.dumps(suite_data, indent=2))
        else:
            typer.echo("Available Benchmark Suites:")
            for suite_name, workflows in benchmarks.items():
                typer.echo(f"  {suite_name}: {len(workflows)} workflows")

    except Exception as e:
        typer.echo(f"✗ Error listing suites: {str(e)}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def list_profiles(
    format: OutputFormat = typer.Option(
        OutputFormat.TEXT,
        help="Output format",
    ),
) -> None:
    """List available workload profiles."""
    try:
        if format == OutputFormat.JSON:
            profiles_data = {
                "standard": [p.value for p in WorkloadProfile],
                "enterprise": list(EnterpriseProfiles.PROFILES.keys()),
            }
            typer.echo(json.dumps(profiles_data, indent=2))
        else:
            typer.echo("Standard Profiles:")
            for profile in WorkloadProfile:
                typer.echo(f"  - {profile.value}")
            typer.echo("\nEnterprise Profiles:")
            for name in EnterpriseProfiles.PROFILES:
                typer.echo(f"  - {name}")

    except Exception as e:
        typer.echo(f"✗ Error listing profiles: {str(e)}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo("HelixOps 1.0.0")
    typer.echo("Production-grade workflow orchestration engine")


if __name__ == "__main__":
    app()

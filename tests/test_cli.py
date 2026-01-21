"""Tests for CLI commands."""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from helixops.cli.app import app
from helixops.generation.models import WorkloadProfile

runner = CliRunner()


class TestGenerateCommand:
    """Tests for generate command."""

    def test_generate_default_profile(self) -> None:
        """Should generate workflow with default profile."""
        result = runner.invoke(app, ["generate", "--profile", "balanced", "--seed", "42"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "workflow_id" in data
        assert "tasks" in data

    def test_generate_tiny_profile(self) -> None:
        """Should generate tiny workflow."""
        result = runner.invoke(app, ["generate", "--profile", "tiny", "--seed", "100"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["tasks"]) < 10

    def test_generate_with_task_override(self) -> None:
        """Should respect task count override."""
        result = runner.invoke(
            app,
            ["generate", "--profile", "balanced", "--seed", "42", "--task-count", "15"],
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["tasks"]) == 15

    def test_generate_to_file(self) -> None:
        """Should write workflow to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "workflow.json"
            result = runner.invoke(
                app,
                ["generate", "--profile", "tiny", "--seed", "42", "--output", str(output_file)],
            )

            assert result.exit_code == 0
            assert output_file.exists()
            data = json.loads(output_file.read_text())
            assert "workflow_id" in data


class TestValidateCommand:
    """Tests for validate command."""

    def test_validate_valid_workflow(self) -> None:
        """Should validate correct workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_file = Path(tmpdir) / "workflow.json"
            workflow_file.write_text(json.dumps({"tasks": {"t1": {}, "t2": {}}}))

            result = runner.invoke(app, ["validate", str(workflow_file)])

            assert result.exit_code == 0
            assert "VALID" in result.stdout

    def test_validate_invalid_workflow(self) -> None:
        """Should reject invalid workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_file = Path(tmpdir) / "workflow.json"
            workflow_file.write_text(json.dumps({}))

            result = runner.invoke(app, ["validate", str(workflow_file)])

            assert result.exit_code == 1

    def test_validate_missing_file(self) -> None:
        """Should fail for missing file."""
        result = runner.invoke(app, ["validate", "/nonexistent/workflow.json"])

        assert result.exit_code == 1

    def test_validate_json_output(self) -> None:
        """Should output JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_file = Path(tmpdir) / "workflow.json"
            workflow_file.write_text(json.dumps({"tasks": {"t1": {}}}))

            result = runner.invoke(
                app,
                ["validate", str(workflow_file), "--format", "json"],
            )

            assert result.exit_code == 0
            data = json.loads(result.stdout)
            assert "valid" in data


class TestBenchmarkCommand:
    """Tests for benchmark command."""

    def test_benchmark_smoke_suite(self) -> None:
        """Should list smoke suite."""
        result = runner.invoke(app, ["benchmark", "--suite", "smoke"])

        assert result.exit_code == 0
        assert "workflows" in result.stdout or "Benchmark" in result.stdout

    def test_benchmark_regression_suite(self) -> None:
        """Should list regression suite."""
        result = runner.invoke(app, ["benchmark", "--suite", "regression"])

        assert result.exit_code == 0

    def test_benchmark_json_output(self) -> None:
        """Should output JSON format."""
        result = runner.invoke(
            app,
            ["benchmark", "--suite", "smoke", "--format", "json"],
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "suite" in data or "workflows" in data

    def test_benchmark_invalid_suite(self) -> None:
        """Should reject invalid suite."""
        result = runner.invoke(app, ["benchmark", "--suite", "invalid"])

        assert result.exit_code == 1


class TestEnterpriseCommand:
    """Tests for enterprise command."""

    def test_enterprise_microservices(self) -> None:
        """Should generate microservices profile."""
        result = runner.invoke(app, ["enterprise", "--profile", "microservices"])

        assert result.exit_code == 0
        assert "microservices" in result.stdout.lower() or "workflow" in result.stdout.lower()

    def test_enterprise_data_pipeline(self) -> None:
        """Should generate data pipeline profile."""
        result = runner.invoke(app, ["enterprise", "--profile", "data_pipeline"])

        assert result.exit_code == 0

    def test_enterprise_json_output(self) -> None:
        """Should output JSON format."""
        result = runner.invoke(
            app,
            ["enterprise", "--profile", "microservices", "--format", "json"],
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "workflow_id" in data

    def test_enterprise_invalid_profile(self) -> None:
        """Should reject invalid profile."""
        result = runner.invoke(app, ["enterprise", "--profile", "invalid"])

        assert result.exit_code == 1


class TestPathologicalCommand:
    """Tests for pathological command."""

    def test_pathological_extreme_depth(self) -> None:
        """Should generate extreme depth case."""
        result = runner.invoke(app, ["pathological", "--case", "extreme_depth"])

        assert result.exit_code == 0
        assert "extreme" in result.stdout.lower() or "workflow" in result.stdout.lower()

    def test_pathological_extreme_width(self) -> None:
        """Should generate extreme width case."""
        result = runner.invoke(app, ["pathological", "--case", "extreme_width"])

        assert result.exit_code == 0

    def test_pathological_json_output(self) -> None:
        """Should output JSON format."""
        result = runner.invoke(
            app,
            ["pathological", "--case", "extreme_depth", "--format", "json"],
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "workflow_id" in data

    def test_pathological_invalid_case(self) -> None:
        """Should reject invalid case."""
        result = runner.invoke(app, ["pathological", "--case", "invalid"])

        assert result.exit_code == 1


class TestListSuitesCommand:
    """Tests for list-suites command."""

    def test_list_suites_text(self) -> None:
        """Should list suites in text format."""
        result = runner.invoke(app, ["list-suites", "--format", "text"])

        assert result.exit_code == 0
        assert "Smoke" in result.stdout or "smoke" in result.stdout

    def test_list_suites_json(self) -> None:
        """Should list suites in JSON format."""
        result = runner.invoke(app, ["list-suites", "--format", "json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "suites" in data


class TestListProfilesCommand:
    """Tests for list-profiles command."""

    def test_list_profiles_text(self) -> None:
        """Should list profiles in text format."""
        result = runner.invoke(app, ["list-profiles", "--format", "text"])

        assert result.exit_code == 0
        assert "tiny" in result.stdout or "Standard" in result.stdout

    def test_list_profiles_json(self) -> None:
        """Should list profiles in JSON format."""
        result = runner.invoke(app, ["list-profiles", "--format", "json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "standard" in data


class TestVersionCommand:
    """Tests for version command."""

    def test_version_output(self) -> None:
        """Should display version."""
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "HelixOps" in result.stdout
        assert "1.0.0" in result.stdout


class TestCLIIntegration:
    """Integration tests for CLI workflows."""

    def test_generate_and_validate_workflow(self) -> None:
        """Should generate and validate workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_file = Path(tmpdir) / "generated.json"

            # Generate
            gen_result = runner.invoke(
                app,
                ["generate", "--profile", "tiny", "--seed", "42", "--output", str(workflow_file)],
            )
            assert gen_result.exit_code == 0

            # Validate
            val_result = runner.invoke(app, ["validate", str(workflow_file)])
            assert val_result.exit_code == 0

    def test_multiple_profile_generation(self) -> None:
        """Should generate multiple profile types."""
        for profile in ["tiny", "balanced", "wide", "deep"]:
            result = runner.invoke(app, ["generate", "--profile", profile, "--seed", "42"])
            assert result.exit_code == 0
            data = json.loads(result.stdout)
            assert len(data["tasks"]) > 0

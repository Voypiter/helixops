"""Workflow validation contracts and rules."""

from helixops.domain.errors import ValidationError
from helixops.domain.models import Workflow


class WorkflowValidator:
    """Validates workflows against business rules."""

    def validate(self, workflow: Workflow) -> tuple[bool, list[str]]:
        """
        Validate a workflow.

        Returns:
            A tuple of (is_valid, list_of_errors).
            If is_valid is True, list_of_errors will be empty.
        """
        errors: list[str] = []

        try:
            self._validate_workflow_metadata(workflow, errors)
            self._validate_graph_structure(workflow, errors)
            self._validate_task_definitions(workflow, errors)
            self._validate_failure_profiles(workflow, errors)
        except ValidationError as e:
            errors.append(str(e))

        return len(errors) == 0, errors

    def validate_or_raise(self, workflow: Workflow) -> None:
        """
        Validate a workflow and raise if invalid.

        Raises:
            ValidationError: If the workflow is invalid.
        """
        is_valid, errors = self.validate(workflow)
        if not is_valid:
            raise ValidationError(f"Workflow validation failed: {'; '.join(errors)}")

    def _validate_workflow_metadata(self, workflow: Workflow, errors: list[str]) -> None:
        """Validate basic workflow metadata."""
        if not workflow.workflow_id or not workflow.workflow_id.strip():
            errors.append("Workflow ID cannot be empty")
        if not workflow.name or not workflow.name.strip():
            errors.append("Workflow name cannot be empty")
        if workflow.get_task_count() == 0:
            errors.append("Workflow must contain at least one task")

    def _validate_graph_structure(self, workflow: Workflow, errors: list[str]) -> None:
        """Validate the dependency graph structure."""
        try:
            workflow.validate()
        except ValidationError as e:
            errors.append(str(e))

    def _validate_task_definitions(self, workflow: Workflow, errors: list[str]) -> None:
        """Validate individual task definitions."""
        for task in workflow.get_all_tasks():
            if not task.task_id or not task.task_id.strip():
                errors.append("Task ID cannot be empty")
            if not task.name or not task.name.strip():
                errors.append(f"Task {task.task_id} must have a non-empty name")
            if task.timeout_seconds is not None and task.timeout_seconds <= 0:
                errors.append(
                    f"Task {task.task_id} has invalid timeout: "
                    f"{task.timeout_seconds} (must be > 0)"
                )

    def _validate_failure_profiles(self, workflow: Workflow, errors: list[str]) -> None:
        """Validate failure profile references."""
        task_ids = {task.task_id for task in workflow.get_all_tasks()}
        for profile in workflow.failure_profiles:
            if profile.task_id not in task_ids:
                errors.append(f"Failure profile references non-existent task: {profile.task_id}")
            if not (0 <= profile.probability <= 1):
                errors.append(
                    f"Failure profile for {profile.task_id} has invalid "
                    f"probability: {profile.probability} (must be in [0, 1])"
                )

"""Pydantic schemas for API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination parameters."""

    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(20, ge=1, le=1000, description="Maximum records to return")


class PaginatedResponse(BaseModel):
    """Generic paginated response."""

    total: int = Field(..., description="Total count of records")
    skip: int = Field(..., description="Records skipped")
    limit: int = Field(..., description="Records returned")
    items: List[Any] = Field(default_factory=list, description="Response items")


class ErrorDetail(BaseModel):
    """Error detail in response."""

    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type")
    request_id: Optional[str] = Field(None, description="Correlation ID")
    details: List[str] = Field(default_factory=list, description="Additional details")


class WorkflowGenerateRequest(BaseModel):
    """Request for workflow generation."""

    profile: str = Field(..., description="Workload profile (tiny, balanced, wide, deep, etc.)")
    seed: int = Field(42, description="Random seed for deterministic generation")
    task_count: Optional[int] = Field(None, description="Override task count")


class WorkflowResponse(BaseModel):
    """API response for a workflow."""

    workflow_id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    task_count: int = Field(..., description="Number of tasks")
    dependency_count: int = Field(..., description="Number of dependencies")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Workflow metadata")


class WorkflowListResponse(BaseModel):
    """Response for workflow list."""

    total: int = Field(..., description="Total workflows")
    workflows: List[WorkflowResponse] = Field(..., description="Workflow list")


class ValidationResponse(BaseModel):
    """Validation result response."""

    valid: bool = Field(..., description="Is workflow valid")
    task_count: int = Field(..., description="Number of tasks")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


class RunCreateRequest(BaseModel):
    """Request to create and run a workflow."""

    workflow_id: str = Field(..., description="Workflow to execute")
    max_concurrent: int = Field(5, ge=1, description="Maximum concurrent tasks")
    seed: Optional[int] = Field(None, description="Execution seed")


class RunResponse(BaseModel):
    """API response for a run."""

    run_id: str = Field(..., description="Unique run identifier")
    workflow_id: str = Field(..., description="Associated workflow ID")
    state: str = Field(..., description="Run state (PENDING, RUNNING, SUCCEEDED, FAILED)")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    duration_ms: Optional[int] = Field(None, description="Total duration in milliseconds")
    task_count: int = Field(..., description="Total tasks")
    succeeded_count: int = Field(0, description="Succeeded tasks")
    failed_count: int = Field(0, description="Failed tasks")


class TaskResponse(BaseModel):
    """API response for a task."""

    task_id: str = Field(..., description="Task identifier")
    task_name: str = Field(..., description="Task name")
    state: str = Field(..., description="Task state")
    attempt_number: int = Field(1, description="Current attempt number")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds")
    error: Optional[str] = Field(None, description="Error message if failed")


class EventResponse(BaseModel):
    """API response for an event."""

    event_id: str = Field(..., description="Event identifier")
    event_type: str = Field(..., description="Event type")
    task_id: Optional[str] = Field(None, description="Associated task ID")
    timestamp: datetime = Field(..., description="Event timestamp")
    duration_ms: Optional[int] = Field(None, description="Event duration")
    error_message: Optional[str] = Field(None, description="Error message if applicable")


class EventListResponse(PaginatedResponse):
    """Paginated events response."""

    items: List[EventResponse] = Field(default_factory=list)


class TaskListResponse(PaginatedResponse):
    """Paginated tasks response."""

    items: List[TaskResponse] = Field(default_factory=list)


class MetricsResponse(BaseModel):
    """System metrics response."""

    total_runs: int = Field(..., description="Total runs executed")
    completed_runs: int = Field(..., description="Completed runs")
    failed_runs: int = Field(..., description="Failed runs")
    total_tasks: int = Field(..., description="Total tasks executed")
    succeeded_tasks: int = Field(..., description="Succeeded tasks")
    failed_tasks: int = Field(..., description="Failed tasks")
    avg_task_duration_ms: float = Field(..., description="Average task duration")
    avg_run_duration_ms: float = Field(..., description="Average run duration")


class RecoveryResponse(BaseModel):
    """Recovery result response."""

    run_id: str = Field(..., description="Recovered run ID")
    recovered: bool = Field(..., description="Recovery successful")
    preserved_tasks: int = Field(..., description="Tasks preserved")
    requeued_tasks: int = Field(..., description="Tasks requeued")
    failed_tasks: int = Field(..., description="Tasks marked failed")


class ReportResponse(BaseModel):
    """Run report response."""

    run_id: str = Field(..., description="Run identifier")
    workflow_id: str = Field(..., description="Workflow identifier")
    status: str = Field(..., description="Final status")
    total_duration_ms: int = Field(..., description="Total duration")
    task_summary: Dict[str, int] = Field(..., description="Task state counts")
    events_count: int = Field(..., description="Total events")
    report_text: str = Field(..., description="Human-readable report")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field("healthy", description="System status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Check timestamp")

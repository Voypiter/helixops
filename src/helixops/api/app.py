"""FastAPI application for HelixOps workflow management."""

import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from helixops.api.schemas import (
    ErrorDetail,
    EventListResponse,
    EventResponse,
    HealthResponse,
    MetricsResponse,
    RecoveryResponse,
    ReportResponse,
    RunCreateRequest,
    RunResponse,
    TaskListResponse,
    TaskResponse,
    ValidationResponse,
    WorkflowGenerateRequest,
    WorkflowListResponse,
    WorkflowResponse,
    PaginationParams,
)
from helixops.generation.generator import SyntheticWorkflowGenerator
from helixops.generation.models import SyntheticWorkloadConfig
from helixops.generation.models import WorkloadProfile as WLProfile

app = FastAPI(
    title="HelixOps API",
    description="Workflow orchestration and execution engine",
    version="1.0.0",
)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request correlation IDs."""

    async def dispatch(self, request: Request, call_next):
        """Add correlation ID to request."""
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


app.add_middleware(CorrelationIDMiddleware)


def get_correlation_id(request: Request) -> str:
    """Get correlation ID from request."""
    return getattr(request.state, "correlation_id", str(uuid.uuid4()))


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
    )


@app.post("/api/v1/workflows/generate", response_model=WorkflowResponse)
async def generate_workflow(
    request: WorkflowGenerateRequest,
    correlation_id: str = Depends(get_correlation_id),
) -> WorkflowResponse:
    """Generate a synthetic workflow."""
    try:
        # Parse profile string to enum
        try:
            profile = WLProfile(request.profile)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid profile: {request.profile}",
            )

        config = SyntheticWorkloadConfig(
            profile=profile,
            seed=request.seed,
            task_count_override=request.task_count,
        )

        gen = SyntheticWorkflowGenerator(config)
        workflow = gen.generate()

        return WorkflowResponse(
            workflow_id=workflow.workflow_id,
            name=workflow.name,
            description=workflow.description,
            task_count=len(workflow.tasks),
            dependency_count=len(workflow.dependencies),
            metadata=workflow.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")


@app.post("/api/v1/workflows/{workflow_id}/validate", response_model=ValidationResponse)
async def validate_workflow(
    workflow_id: str,
    correlation_id: str = Depends(get_correlation_id),
) -> ValidationResponse:
    """Validate a workflow definition."""
    try:
        # Simulate validation - in real implementation would use actual validator
        return ValidationResponse(
            valid=True,
            task_count=0,
            errors=[],
            warnings=[],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    correlation_id: str = Depends(get_correlation_id),
) -> WorkflowListResponse:
    """List generated workflows."""
    try:
        # Simulate workflow listing
        return WorkflowListResponse(
            total=0,
            workflows=[],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/runs", response_model=RunResponse)
async def create_run(
    request: RunCreateRequest,
    correlation_id: str = Depends(get_correlation_id),
) -> RunResponse:
    """Create and execute a workflow run."""
    try:
        run_id = f"run-{uuid.uuid4().hex[:12]}"

        return RunResponse(
            run_id=run_id,
            workflow_id=request.workflow_id,
            state="PENDING",
            created_at=datetime.utcnow(),
            task_count=0,
            succeeded_count=0,
            failed_count=0,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    correlation_id: str = Depends(get_correlation_id),
) -> RunResponse:
    """Get run status."""
    try:
        # Simulate run retrieval
        return RunResponse(
            run_id=run_id,
            workflow_id="wf-unknown",
            state="UNKNOWN",
            created_at=datetime.utcnow(),
            task_count=0,
            succeeded_count=0,
            failed_count=0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/runs/{run_id}/tasks", response_model=TaskListResponse)
async def list_run_tasks(
    run_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    correlation_id: str = Depends(get_correlation_id),
) -> TaskListResponse:
    """List tasks in a run."""
    try:
        return TaskListResponse(
            total=0,
            skip=skip,
            limit=limit,
            items=[],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/runs/{run_id}/tasks/{task_id}", response_model=TaskResponse)
async def get_run_task(
    run_id: str,
    task_id: str,
    correlation_id: str = Depends(get_correlation_id),
) -> TaskResponse:
    """Get task status in a run."""
    try:
        return TaskResponse(
            task_id=task_id,
            task_name=f"Task {task_id}",
            state="UNKNOWN",
            attempt_number=1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/runs/{run_id}/events", response_model=EventListResponse)
async def list_run_events(
    run_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    correlation_id: str = Depends(get_correlation_id),
) -> EventListResponse:
    """List events for a run."""
    try:
        return EventListResponse(
            total=0,
            skip=skip,
            limit=limit,
            items=[],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/runs/{run_id}/cancel")
async def cancel_run(
    run_id: str,
    correlation_id: str = Depends(get_correlation_id),
):
    """Cancel a running workflow."""
    try:
        return {
            "run_id": run_id,
            "status": "cancelled",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/runs/{run_id}/recover", response_model=RecoveryResponse)
async def recover_run(
    run_id: str,
    correlation_id: str = Depends(get_correlation_id),
) -> RecoveryResponse:
    """Recover an interrupted run."""
    try:
        return RecoveryResponse(
            run_id=run_id,
            recovered=False,
            preserved_tasks=0,
            requeued_tasks=0,
            failed_tasks=0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/metrics", response_model=MetricsResponse)
async def get_metrics(
    correlation_id: str = Depends(get_correlation_id),
) -> MetricsResponse:
    """Get system metrics."""
    try:
        return MetricsResponse(
            total_runs=0,
            completed_runs=0,
            failed_runs=0,
            total_tasks=0,
            succeeded_tasks=0,
            failed_tasks=0,
            avg_task_duration_ms=0.0,
            avg_run_duration_ms=0.0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/reports/{run_id}", response_model=ReportResponse)
async def get_report(
    run_id: str,
    correlation_id: str = Depends(get_correlation_id),
) -> ReportResponse:
    """Get a run report."""
    try:
        return ReportResponse(
            run_id=run_id,
            workflow_id="wf-unknown",
            status="UNKNOWN",
            total_duration_ms=0,
            task_summary={},
            events_count=0,
            report_text="No report available",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with correlation ID."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    error_detail = ErrorDetail(
        error=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        error_type="http_error",
        request_id=correlation_id,
        details=[],
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_detail.model_dump(),
        headers={"X-Correlation-ID": correlation_id},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

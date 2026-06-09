"""Tests for FastAPI endpoints."""

from fastapi.testclient import TestClient

from helixops.api.app import app

client = TestClient(app)


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self) -> None:
        """Should return health status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_health_check_has_correlation_id(self) -> None:
        """Should include correlation ID in response."""
        response = client.get("/health")

        assert "X-Correlation-ID" in response.headers


class TestWorkflowGeneration:
    """Tests for workflow generation endpoint."""

    def test_generate_workflow_balanced(self) -> None:
        """Should generate balanced workflow."""
        payload = {
            "profile": "balanced",
            "seed": 42,
        }

        response = client.post("/api/v1/workflows/generate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data
        assert "name" in data
        assert "task_count" in data

    def test_generate_workflow_with_task_override(self) -> None:
        """Should respect task count override."""
        payload = {
            "profile": "tiny",
            "seed": 42,
            "task_count": 10,
        }

        response = client.post("/api/v1/workflows/generate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["task_count"] == 10

    def test_generate_workflow_invalid_profile(self) -> None:
        """Should reject invalid profile."""
        payload = {
            "profile": "invalid_profile",
            "seed": 42,
        }

        response = client.post("/api/v1/workflows/generate", json=payload)

        assert response.status_code == 400

    def test_generate_has_correlation_id(self) -> None:
        """Should include correlation ID in response."""
        payload = {
            "profile": "tiny",
            "seed": 42,
        }

        response = client.post("/api/v1/workflows/generate", json=payload)

        assert "X-Correlation-ID" in response.headers


class TestWorkflowValidation:
    """Tests for workflow validation endpoint."""

    def test_validate_workflow(self) -> None:
        """Should validate workflow."""
        response = client.post("/api/v1/workflows/wf-test/validate")

        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "errors" in data


class TestWorkflowListing:
    """Tests for workflow listing endpoint."""

    def test_list_workflows(self) -> None:
        """Should list workflows."""
        response = client.get("/api/v1/workflows")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "workflows" in data

    def test_list_workflows_pagination(self) -> None:
        """Should support pagination."""
        response = client.get("/api/v1/workflows?skip=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0


class TestRunCreation:
    """Tests for run creation endpoint."""

    def test_create_run(self) -> None:
        """Should create a run."""
        payload = {
            "workflow_id": "wf-test",
            "max_concurrent": 5,
        }

        response = client.post("/api/v1/runs", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["workflow_id"] == "wf-test"
        assert "state" in data

    def test_create_run_with_seed(self) -> None:
        """Should accept execution seed."""
        payload = {
            "workflow_id": "wf-test",
            "max_concurrent": 5,
            "seed": 123,
        }

        response = client.post("/api/v1/runs", json=payload)

        assert response.status_code == 200


class TestRunInspection:
    """Tests for run inspection endpoints."""

    def test_get_run(self) -> None:
        """Should get run status."""
        response = client.get("/api/v1/runs/run-test")

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "run-test"
        assert "state" in data

    def test_list_run_tasks(self) -> None:
        """Should list run tasks."""
        response = client.get("/api/v1/runs/run-test/tasks")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_run_tasks_pagination(self) -> None:
        """Should support pagination for tasks."""
        response = client.get("/api/v1/runs/run-test/tasks?skip=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "skip" in data
        assert "limit" in data

    def test_get_run_task(self) -> None:
        """Should get task status in run."""
        response = client.get("/api/v1/runs/run-test/tasks/task-1")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-1"
        assert "state" in data

    def test_list_run_events(self) -> None:
        """Should list run events."""
        response = client.get("/api/v1/runs/run-test/events")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestRunControl:
    """Tests for run control endpoints."""

    def test_cancel_run(self) -> None:
        """Should cancel a run."""
        response = client.post("/api/v1/runs/run-test/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "run-test"

    def test_recover_run(self) -> None:
        """Should recover a run."""
        response = client.post("/api/v1/runs/run-test/recover")

        assert response.status_code == 200
        data = response.json()
        assert "recovered" in data
        assert "preserved_tasks" in data


class TestMetrics:
    """Tests for metrics endpoint."""

    def test_get_metrics(self) -> None:
        """Should get system metrics."""
        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "total_runs" in data
        assert "completed_runs" in data
        assert "total_tasks" in data
        assert "avg_task_duration_ms" in data


class TestReports:
    """Tests for report export endpoint."""

    def test_get_report(self) -> None:
        """Should get run report."""
        response = client.get("/api/v1/reports/run-test")

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "run-test"
        assert "status" in data
        assert "report_text" in data


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_error(self) -> None:
        """Should return 404 for missing endpoints."""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_invalid_json(self) -> None:
        """Should handle invalid JSON."""
        response = client.post(
            "/api/v1/workflows/generate",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code >= 400


class TestCorrelationID:
    """Tests for request correlation IDs."""

    def test_default_correlation_id(self) -> None:
        """Should generate correlation ID if not provided."""
        response = client.get("/health")

        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) > 0

    def test_custom_correlation_id(self) -> None:
        """Should preserve provided correlation ID."""
        custom_id = "test-correlation-123"
        response = client.get(
            "/health",
            headers={"X-Correlation-ID": custom_id},
        )

        assert response.headers["X-Correlation-ID"] == custom_id

    def test_correlation_id_in_error(self) -> None:
        """Should include correlation ID in error responses."""
        payload = {
            "profile": "invalid",
            "seed": 42,
        }

        response = client.post(
            "/api/v1/workflows/generate",
            json=payload,
        )

        assert "X-Correlation-ID" in response.headers


class TestAPIPagination:
    """Tests for API pagination."""

    def test_pagination_skip_limit(self) -> None:
        """Should handle skip and limit parameters."""
        response = client.get("/api/v1/runs/run-test/tasks?skip=5&limit=15")

        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 5
        assert data["limit"] == 15

    def test_pagination_defaults(self) -> None:
        """Should use default pagination values."""
        response = client.get("/api/v1/runs/run-test/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 0
        assert data["limit"] == 20

    def test_pagination_max_limit(self) -> None:
        """Should reject limit above maximum."""
        response = client.get("/api/v1/runs/run-test/tasks?limit=10000")

        # Should return 422 validation error for limit > 100
        assert response.status_code in [200, 422]


class TestRequestTracing:
    """Tests for request tracing and correlation."""

    def test_request_context_creation(self) -> None:
        """Should create request context."""
        from helixops.api.tracing import RequestContext

        context = RequestContext("test-request-1")

        assert context.request_id == "test-request-1"
        assert context.get_duration_ms() >= 0

    def test_request_context_tags(self) -> None:
        """Should track tags in context."""
        from helixops.api.tracing import RequestContext

        context = RequestContext("test-request-1")
        context.tag("endpoint", "/api/workflows")
        context.tag("method", "POST")

        assert context.tags["endpoint"] == "/api/workflows"
        assert context.tags["method"] == "POST"

    def test_request_context_measurements(self) -> None:
        """Should record measurements."""
        from helixops.api.tracing import RequestContext

        context = RequestContext("test-request-1")
        context.measure("db_time_ms", 42.5)
        context.measure("task_count", 10.0)

        assert context.measurements["db_time_ms"] == 42.5
        assert context.measurements["task_count"] == 10.0

    def test_request_tracer(self) -> None:
        """Should manage request contexts."""
        from helixops.api.tracing import RequestTracer

        tracer = RequestTracer()
        context1 = tracer.create_context("req-1")
        context2 = tracer.create_context("req-2")

        assert tracer.get_context("req-1") == context1
        assert tracer.get_context("req-2") == context2

    def test_request_diagnostics(self) -> None:
        """Should track request diagnostics."""
        from helixops.api.tracing import RequestDiagnostics

        diag = RequestDiagnostics()
        diag.record_request("/api/workflows", "POST")
        diag.record_request("/api/workflows", "GET")
        diag.record_error("/api/workflows", "validation_error")

        summary = diag.get_summary()

        assert summary["total_requests"] == 2
        assert summary["total_errors"] == 1


class TestSchemaValidation:
    """Tests for request/response schema validation."""

    def test_generate_response_schema(self) -> None:
        """Should return correctly formatted workflow response."""
        payload = {
            "profile": "tiny",
            "seed": 42,
        }

        response = client.post("/api/v1/workflows/generate", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        required_fields = ["workflow_id", "name", "description", "task_count", "dependency_count"]
        for field in required_fields:
            assert field in data

    def test_run_response_schema(self) -> None:
        """Should return correctly formatted run response."""
        response = client.get("/api/v1/runs/run-test")

        assert response.status_code == 200
        data = response.json()

        required_fields = ["run_id", "workflow_id", "state", "created_at", "task_count"]
        for field in required_fields:
            assert field in data

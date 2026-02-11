"""Request tracing and correlation for API diagnostics."""

import time
from typing import Dict, Optional
from uuid import uuid4

from fastapi import Request


class RequestContext:
    """Request-scoped operational context."""

    def __init__(self, request_id: str):
        """Initialize request context.

        Args:
            request_id: Unique request identifier
        """
        self.request_id = request_id
        self.start_time = time.time()
        self.tags: Dict[str, str] = {}
        self.measurements: Dict[str, float] = {}

    def tag(self, key: str, value: str) -> None:
        """Add a tag to the request context.

        Args:
            key: Tag key
            value: Tag value
        """
        self.tags[key] = value

    def measure(self, key: str, value: float) -> None:
        """Record a measurement.

        Args:
            key: Measurement key
            value: Measurement value
        """
        self.measurements[key] = value

    def get_duration_ms(self) -> float:
        """Get elapsed time in milliseconds.

        Returns:
            Duration since context creation in milliseconds
        """
        return (time.time() - self.start_time) * 1000

    def to_dict(self) -> Dict:
        """Convert context to dictionary.

        Returns:
            Context as dictionary
        """
        return {
            "request_id": self.request_id,
            "duration_ms": self.get_duration_ms(),
            "tags": self.tags,
            "measurements": self.measurements,
        }


class RequestTracer:
    """Traces and correlates requests across the system."""

    def __init__(self):
        """Initialize request tracer."""
        self.contexts: Dict[str, RequestContext] = {}
        self.max_contexts = 1000

    def create_context(self, request_id: Optional[str] = None) -> RequestContext:
        """Create a new request context.

        Args:
            request_id: Optional request ID (generated if not provided)

        Returns:
            New RequestContext
        """
        if request_id is None:
            request_id = str(uuid4())

        # Cleanup old contexts if needed
        if len(self.contexts) > self.max_contexts:
            # Remove oldest contexts
            oldest_keys = sorted(
                self.contexts.keys(),
                key=lambda k: self.contexts[k].start_time,
            )[:self.max_contexts // 2]
            for key in oldest_keys:
                del self.contexts[key]

        context = RequestContext(request_id)
        self.contexts[request_id] = context
        return context

    def get_context(self, request_id: str) -> Optional[RequestContext]:
        """Get a request context by ID.

        Args:
            request_id: Request ID

        Returns:
            RequestContext or None if not found
        """
        return self.contexts.get(request_id)

    def complete_context(self, request_id: str) -> Optional[Dict]:
        """Mark a context as completed and return its summary.

        Args:
            request_id: Request ID

        Returns:
            Context summary dictionary or None
        """
        context = self.contexts.get(request_id)
        if context:
            summary = context.to_dict()
            # Keep context for audit but mark duration as final
            return summary
        return None


class RequestDiagnostics:
    """Diagnostics information for API requests."""

    def __init__(self):
        """Initialize diagnostics."""
        self.tracer = RequestTracer()
        self.request_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}

    def record_request(self, endpoint: str, method: str) -> str:
        """Record a new request.

        Args:
            endpoint: API endpoint
            method: HTTP method

        Returns:
            Request ID for correlation
        """
        request_id = str(uuid4())
        context = self.tracer.create_context(request_id)
        context.tag("endpoint", endpoint)
        context.tag("method", method)

        key = f"{method} {endpoint}"
        self.request_counts[key] = self.request_counts.get(key, 0) + 1

        return request_id

    def record_error(self, endpoint: str, error_type: str) -> None:
        """Record an error for an endpoint.

        Args:
            endpoint: API endpoint
            error_type: Type of error
        """
        key = f"{endpoint}:{error_type}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1

    def get_summary(self) -> Dict:
        """Get diagnostics summary.

        Returns:
            Dictionary with diagnostics information
        """
        return {
            "total_requests": sum(self.request_counts.values()),
            "total_errors": sum(self.error_counts.values()),
            "endpoints": len(self.request_counts),
            "request_counts": self.request_counts,
            "error_counts": self.error_counts,
            "active_contexts": len(self.tracer.contexts),
        }


# Global tracer instance
_global_tracer = RequestTracer()
_global_diagnostics = RequestDiagnostics()


def get_global_tracer() -> RequestTracer:
    """Get the global request tracer.

    Returns:
        Global RequestTracer instance
    """
    return _global_tracer


def get_global_diagnostics() -> RequestDiagnostics:
    """Get the global diagnostics instance.

    Returns:
        Global RequestDiagnostics instance
    """
    return _global_diagnostics

# HelixOps: Self-Healing Distributed Workflow Simulation Platform

A production-grade Python platform that simulates, schedules, executes, observes, and repairs complex distributed workflows without relying on external data.

## Overview

HelixOps provides an internal reliability engineering platform that lets companies test how workflow systems behave under failures before deploying real automation pipelines. The system programmatically generates workloads, injects failures, persists execution state, retries failed jobs intelligently, exposes metrics, and validates correctness through deterministic tests.

## Architecture

HelixOps is organized into 10 major layers:

1. **Core Domain Layer** — Workflow definitions, task definitions, dependency graphs, task states, execution events, retry policies, failure models, and validation rules.
2. **DAG Planning Engine** — Graph validation, cycle detection, executable task waves, dependency resolution, and execution plan generation.
3. **Execution Engine** — Asynchronous task execution, dependency ordering, timeouts, retries, failure isolation, state recording, and cancellation.
4. **Persistence Layer** — Durable storage using SQLite with repository abstraction for future storage backends.
5. **Failure Simulation Layer** — Deterministic synthetic failure injection with seed-driven randomness.
6. **Recovery Layer** — Run restoration, inconsistency detection, task re-queueing, and audit trail generation.
7. **Observability Layer** — Structured logs, metrics, traces, health checks, counters, histograms, and execution summaries.
8. **API Layer** — FastAPI service for workflow/run management, status inspection, cancellation, metrics, and recovery.
9. **CLI Layer** — Typer-based CLI for workload generation, execution, failure injection, and report viewing.
10. **Test and Benchmark Layer** — Deterministic test suite generation, edge-case DAGs, stress workloads, and benchmark reports.

## Project Status

- **v0.1.0 (Current)** — Domain model and validation contracts.

## Installation

```bash
pip install -e .
```

## Development Setup

```bash
pip install -e ".[dev]"
pre-commit install
```

## Running Tests

```bash
pytest
pytest --cov=src/helixops
```

## License

MIT

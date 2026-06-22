# HelixOps: Distributed Workflow Orchestration Engine

A production-grade Python framework for reliable, observable workflow execution with deterministic testing, crash recovery, and comprehensive performance optimization.

**Status:** Production-ready (Milestone 12)  
**Test Coverage:** 241+ tests  
**Python Version:** 3.11+  
**License:** MIT

## Quick Start

### Local Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest tests/ -v

# Start API server
python -m uvicorn helixops.api.app:app --reload

# Run CLI
helixops generate --profile balanced --seed 42
helixops validate workflow.json
```

### Docker Deployment

```bash
# Build image
docker build -t helixops:latest .

# Run API server
docker run -p 8000:8000 \
  -e HELIXOPS_ENV=production \
  -e HELIXOPS_MAX_CONCURRENT=100 \
  helixops:latest
```

## Configuration

HelixOps uses environment variables for runtime configuration. See Configuration section below for full options.

## CLI Usage

### Generate Workflows

```bash
helixops generate --profile balanced --seed 42
helixops generate --profile tiny --seed 100
helixops validate workflow.json
helixops benchmark --suite smoke
```

### Profiles

- **tiny:** 5 tasks, minimal dependencies
- **balanced:** 50 tasks, moderate parallelism
- **wide:** 100+ parallel tasks
- **deep:** Sequential chain of 100+ tasks
- **failure_heavy:** 50% failure rate for testing
- **enterprise:** Real-world microservices patterns
- **stress:** Maximum scale workloads

## API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

### Generate Workflow

```bash
curl -X POST http://localhost:8000/api/v1/workflows/generate \
  -H "Content-Type: application/json" \
  -d '{"profile": "balanced", "seed": 42}'
```

### Create and Execute Run

```bash
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "wf-abc", "max_concurrent": 10}'
```

### Recover Interrupted Run

```bash
curl -X POST http://localhost:8000/api/v1/runs/run-xyz/recover
```

## Recovery and Crash Safety

HelixOps implements conservative crash recovery:

1. **At-least-once execution** after recovery
2. **No duplicate execution** under any failure scenario
3. **Eventual consistency** of event audit trail
4. **Atomic state transitions** with database transactions

On restart after crash:
- Successfully completed tasks are preserved
- Running tasks are marked failed (unsafe to resume)
- Queued tasks are requeued for execution
- Full audit trail is generated

## Benchmarking

```bash
# Run benchmark suite
helixops benchmark --suite smoke
helixops benchmark --suite regression
helixops benchmark --suite scalability

# Performance expectations (typical hardware):
# - Tiny (5 tasks): <200ms
# - Balanced (50 tasks): <2000ms
# - Wide (100 parallel): <5000ms
# - Deep (100 sequential): <10000ms
```

## Operational Limitations

### Resource Constraints

- Max concurrent tasks: 500
- Max workflow size: 10,000 tasks
- Max task timeout: 3600 seconds
- Max API request size: 10 MB
- Event retention: 7 days

### Scalability Notes

- Wide workflows: Use batched event persistence
- Deep workflows: Linear execution, no parallelism gains
- High throughput: Enable connection pooling and batch writes

### Known Limitations

- Single-node only (no distributed execution)
- SQLite default (use PostgreSQL for production)
- No built-in scheduling
- No secret management

## Architecture

### Core Components

1. **Domain Model** — Workflow, Task, Execution concepts
2. **Planning** — DAG construction, cycle detection
3. **Execution** — Async task runtime with bounded concurrency
4. **Retry Policy** — Failure classification and backoff
5. **Persistence** — SQLAlchemy ORM and event journaling
6. **Recovery** — Crash recovery and reconciliation
7. **Workload Generation** — Deterministic synthetic workflows
8. **CLI** — Typer-based command-line interface
9. **API** — FastAPI HTTP service
10. **Observability** — Metrics, health checks, diagnostics
11. **Benchmarking** — Performance measurement
12. **Configuration** — Runtime settings and validation
13. **Lifecycle** — Graceful shutdown and deployment

## Development

### Running Tests

```bash
pytest tests/ -v
pytest tests/ --cov=src/helixops
```

### Project Structure

- `src/helixops/` — Production code (74 modules)
- `tests/` — Test suite (241+ tests)
- `docs/adr/` — Architecture decision records
- `Dockerfile` — Container image

## License

MIT


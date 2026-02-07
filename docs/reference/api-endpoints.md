# API Endpoint Reference

| Method | Path | Purpose |
|--------|------|---------|
| GET | /health | Liveness check |
| POST | /api/v1/workflows/generate | Generate a synthetic workflow |
| POST | /api/v1/runs | Create and execute a run |
| GET | /api/v1/runs/{id} | Inspect run status |
| POST | /api/v1/runs/{id}/recover | Recover an interrupted run |

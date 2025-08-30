# HelixOps Architecture (Early Design)

A layered system separating concerns:
- Domain: workflow, task, dependency graph
- Planning: DAG validation, cycle detection, topological ordering
- Execution: async tasks with bounded concurrency
- Persistence: event journal + repository pattern
- Recovery: conservative reconciliation after crashes
- Observability: metrics, health, diagnostics
- API: FastAPI for workflows, runs, metrics

Each layer is designed to be testable and replaceable.

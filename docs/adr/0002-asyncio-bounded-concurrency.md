# ADR 0002: Asyncio with Bounded Concurrency via Semaphore

## Status
Accepted

## Context

HelixOps needs to execute many tasks concurrently but must limit resource usage. We must choose between:
1. Thread pool with fixed size
2. Process pool with fixed size
3. Async (asyncio) with semaphore-based concurrency control
4. Full distributed execution (out of scope)

## Decision

Use **asyncio with asyncio.Semaphore** for bounded concurrency control.

### Rationale

1. **Python Native** — asyncio is built-in, no external dependencies
2. **Resource Efficient** — Thousands of tasks with few threads
3. **Deterministic Testing** — Async allows reproducible failure injection with seeds
4. **Single-node Scope** — HelixOps is single-node, asyncio is sufficient
5. **Simplicity** — Easier to reason about than thread safety

### Implementation

```python
semaphore = asyncio.Semaphore(max_concurrent)

async def execute_task(task):
    async with semaphore:
        # Task runs here, limited to max_concurrent tasks
        return await do_work(task)

# Execute all tasks with concurrency limit
await asyncio.gather(*[execute_task(t) for t in tasks])
```

## Trade-offs

- **Pro:** Single-threaded, no GIL worries
- **Pro:** Deterministic execution with seeded randomness
- **Pro:** Built-in, zero external dependencies
- **Con:** I/O bound only (no CPU parallelism)
- **Con:** Crash during execution loses in-flight state

## Consequences

1. Max concurrency is limited by single process
2. All work is I/O-bound (suitable for orchestration)
3. Crash recovery must persist frequently (solved via async event journaling)
4. Tests are reproducible with seeds
5. Single-node only (no horizontal scaling)

# ADR 0001: Conservative Crash Recovery Strategy

## Status
Accepted

## Context

HelixOps must handle process crashes safely. When a crash occurs during task execution, we need to decide what state to recover to and how to resume work.

The key tension is between:
1. **Maximizing progress recovery** — Resume as many tasks as possible
2. **Preventing duplicate execution** — Never run a task twice
3. **Maintaining consistency** — Ensure audit trail reflects actual work

## Decision

Implement **conservative crash recovery**: On restart after crash, preserve completed tasks but mark running tasks as failed (unsafe to resume).

### Rationale

1. **Safety First** — No duplicate execution risk under any failure scenario
2. **Simplicity** — Clear semantics: "running at crash time" = "unknown state"
3. **Audit Integrity** — Recovery audit trail accurately reflects what happened
4. **Correctness** — Tasks may have side effects; resuming them is unsafe

### Trade-offs

- **Pro:** Guarantees no duplicate execution
- **Pro:** Recovery is fast (just mark running tasks failed)
- **Pro:** Audit trail is accurate
- **Con:** May re-execute some completed work on recovery (acceptable cost)
- **Con:** Operator must manually inspect recovery audit trail

## Implementation

```python
# On crash recovery:
for task in get_running_tasks(run_id):
    # Don't resume running tasks - unknown state
    mark_as_failed(task, reason="crashed_while_running")

for task in get_completed_tasks(run_id):
    # Preserve completed work
    preserve(task)

for task in get_queued_tasks(run_id):
    # Requeue pending work
    requeue(task)
```

## Consequences

1. Runs are guaranteed safe to resume after crash
2. No duplicate task execution under any failure scenario
3. Some work may be repeated (conservative cost)
4. Recovery is O(1) — independent of task count
5. Users can inspect recovery audit trail to understand what was lost

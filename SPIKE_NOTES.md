# Initial Spike Notes (Aug 2025)

## Explorations
1. Asyncio for execution — chosen for determinism, simplicity, test control
2. SQLite for v1 storage — chosen for low operational burden; Postgres TBD
3. Event-sourced journal — tested append-only design for recovery safety
4. Topological waves — initial scheduler model; known limitation is collective
   barrier, but good enough for MVP

## Open Questions (to be addressed post-M1)
- How to scale to 100K tasks in a single workflow?
- Multi-instance coordination story?
- Real-time observability vs. event reconstruction?

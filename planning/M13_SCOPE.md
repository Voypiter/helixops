# M13 Scope: Scheduler & Concurrency Evolution

## Objectives
1. Replace wave barriers with continuous ready-frontier scheduler
2. Add per-task timeout and cancellation isolation
3. Measure and validate throughput improvements

## Success Criteria
- 8K parallel tasks: reach 80%+ CPU utilization (vs 40% today)
- Zero test regressions
- Backwards-compatible API

## Known Risks
- Scheduler logic becomes more complex; needs property-based testing
- May surface latent race conditions

## Timeline
- Design: Apr 1–10
- Implementation: Apr 11–20
- Testing and refinement: Apr 21–30
- Merge: May 1

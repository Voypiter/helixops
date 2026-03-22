# Operational Learnings (Q1 2026)

## What Worked
- Deterministic reproduction from seeds — caught and fixed 3 bugs that would
  have taken weeks without it
- Conservative recovery — despite slowness, never lost data integrity
- Event journal — incident diagnosis went from "unknown" to "root cause
  identified" in hours

## What Needs Work
- Single-node assumptions are invisible until you hit them
- Health checks (liveness-only) do not catch DB outages
- Graceful shutdown does not drain gracefully under load
- No circuit breakers for systemic failures

## Org Impact
- On-call load increased 3x in March (incidents: wave stall, SQLite, OOM)
- Recovery time improved with OTel tracing (M17 will help further)
- Team confidence: cautious. Need quick wins (M13) before scale-out (M16)

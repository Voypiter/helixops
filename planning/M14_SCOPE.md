# M14 Scope: Persistence Scaling & Migrations

## Objectives
1. Add Postgres repository implementation (drop-in for SQLite)
2. Alembic versioned migrations
3. Event-table partitioning by date

## Success Criteria
- Concurrent writes from multiple instances
- Event queries remain <100ms even at 1M rows
- Schema upgrades are reviewable and reversible

## Known Risks
- Introduces operational dependency on Postgres
- Migration failure during deploy must be graceful

## Timeline
- Design: May 1–10
- Implementation: May 11–25
- Deploy and verification: May 26–31

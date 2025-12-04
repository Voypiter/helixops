# Persistence Schema Design Notes

Maps domain objects to relational tables: runs, task attempts, and the
append-only event journal. Documents the transactional boundaries and
the reasoning behind storing attempts as first-class records.

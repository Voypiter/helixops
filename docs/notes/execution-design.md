# Execution Engine Design Notes

The runtime executes topological waves under a bounded semaphore. These
notes capture the rationale for wave-based scheduling, the cancellation
model, and the determinism guarantees provided by seeded execution.

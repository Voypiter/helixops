"""Fixtures exercising bounded-concurrency behaviour."""

# A wide wave that should be capped by the semaphore.
WIDE_WAVE = {"tasks": {f"t{i}": {} for i in range(128)}}

# A deep chain with no available parallelism.
DEEP_CHAIN = {"tasks": {"t0": {}, **{f"t{i}": {"deps": [f"t{i-1}"]} for i in range(1, 64)}}}

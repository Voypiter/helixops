# Recovery Decision Matrix

For each observed task state at crash time, this matrix defines the
conservative recovery action: preserve, requeue, or mark failed. The
guiding invariant is that no task is ever executed twice.

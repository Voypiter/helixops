# Incident Report: In-Memory State OOM

Date: March 2026
Severity: Critical
Duration: 2 hours (recovery)

## What Happened
Batch customer submitted 60K-task workflow. Process accumulated events in
memory and was OOM-killed at task 41K. Run lost, re-executed tasks saw
duplicate side effects downstream.

## Root Cause
Execution engine holds full event list + task state in RAM. O(tasks + events)
memory growth.

## Resolution
M15: streaming event persistence with bounded backpressure.

## Action Items
- Add memory profiling to benchmarks (M15)
- Document per-task memory budget (M13)

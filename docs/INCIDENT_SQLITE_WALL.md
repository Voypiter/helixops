# Incident Report: SQLite Single-Writer Bottleneck

Date: March 2026
Severity: Critical
Duration: 45 minutes

## What Happened
Second instance added for HA; within minutes, recovery and execution contended
for SQLite lock, cascading into SQLITE_BUSY errors and timeouts.

## Root Cause
SQLite single-writer assumption; no cross-instance coordination.

## Resolution
Rolled back second instance; committed to Postgres in M14.

## Lessons
- Every global assumption must be documented
- Instance count validation needed at startup

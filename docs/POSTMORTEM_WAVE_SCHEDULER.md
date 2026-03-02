# Postmortem: Wave Scheduler Throughput Ceiling

Date: March 2026
Severity: High
Status: Planned for M13

## Timeline
- Feb 25: First production customer with 8K parallel tasks reports 40% utilization
- Feb 28: Root cause identified: wave barrier (slowest task stalls siblings)
- Mar 5: Architecture approved for ready-frontier scheduler replacement

## Impact
- 5–10 customer workflows affected
- Throughput recoverable to 85% with M13 work

## Follow-up
Ready-frontier scheduler in progress.

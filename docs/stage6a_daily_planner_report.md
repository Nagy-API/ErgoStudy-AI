# Daily planner report

The deterministic planner remains unchanged. It scores subjects with `0.35 × priority + 0.25 × workload + 0.20 × difficulty + 0.20 × knowledge gap`, allocates useful study blocks within available time, schedules 20-to-60-minute study sessions, and inserts configured five- or ten-minute timer-based breaks.

The same request and active configuration produce the same plan ID and schedule. Aliases, optional topics, unknown-subject fallback, unscheduled subjects, start times, totals, and positive-duration constraints remain covered by tests. The planner has no hardware input or adaptation path.

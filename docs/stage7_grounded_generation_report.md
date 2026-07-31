# Grounded generation report

Local `qwen3:4b-instruct` is an optional wording layer for completed study plans. It receives allow-listed plan and retrieval context and returns strict JSON containing a summary, allocation explanations, session messages, an optional unscheduled-subject message, and warnings.

Validation preserves exact subjects, allocations, sessions, durations, warnings, and safe general language. One correction attempt is allowed. Ollama unavailability, timeout, malformed JSON, or invalid content returns a validated deterministic fallback. Medical-diagnosis protection remains generally applicable. No sensor context, action, notice, or output field exists.

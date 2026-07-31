# Flutter integration guide

Flutter sends study-planning data only. The physical product's sensors remain entirely inside hardware/Flutter ownership and must not be forwarded to this API. Users with and without sensor hardware receive identical AI study-planning capabilities.

Use `/api/v1/plans` for the normal fast path. It returns immediately from deterministic local services and never waits for Ollama. Use `/api/v1/explanations` only when optional wording is requested; treat `deterministic_fallback` as success. `/api/v1/plans/full-with-explanation` is for demonstrations, not the primary UI path.

Recommended transport models: `PlanRequest`, `SubjectInput`, `PlanResponse`, `DailyStudyPlan`, `ScheduledSubject`, `PlannedSession`, `FallbackInformation`, `ExplanationResponse`, and `ApiError`. Generate exact models from `/openapi.json`; preserve nullable fields instead of replacing them with empty strings.

Use a short local timeout such as five seconds for deterministic calls and a longer timeout for explanation calls. Log `request_id` for support. Parse HTTP 422 using the documented error envelope. Do not send unknown fields because the API rejects them.

The Flutter UI may separately display hardware information, but it must not imply that the backend used it or that hardware owners receive extra AI features.

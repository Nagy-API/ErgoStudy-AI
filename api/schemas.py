"""Strict Pydantic request and response schemas for API version 1."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


API_VERSION = "v1"
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
SubjectName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
TopicName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Rating = Annotated[int, Field(strict=True, ge=1, le=5)]
PositiveInteger = Annotated[int, Field(strict=True, ge=1)]
NonNegativeInteger = Annotated[int, Field(strict=True, ge=0)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SubjectRequest(StrictModel):
    name: SubjectName
    topics: list[TopicName] = Field(default_factory=list, max_length=20)
    difficulty: Rating
    priority: Rating
    workload: Rating
    current_understanding: Rating

    @field_validator("topics")
    @classmethod
    def reject_duplicate_topics(cls, topics: list[str]) -> list[str]:
        normalized = [" ".join(topic.casefold().split()) for topic in topics]
        if len(normalized) != len(set(normalized)):
            raise ValueError("duplicate topics are not allowed within one subject")
        return topics


class PlanRequest(StrictModel):
    total_available_minutes: Annotated[int, Field(strict=True, ge=30, le=720)]
    preferred_start_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    preferred_session_length: Annotated[int, Field(strict=True, ge=20, le=60)] | None = None
    subjects: list[SubjectRequest] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def reject_duplicate_subjects(self) -> "PlanRequest":
        normalized = [" ".join(item.name.casefold().split()) for item in self.subjects]
        if len(normalized) != len(set(normalized)):
            raise ValueError("duplicate subject names are not allowed")
        return self


class PlannedSessionSchema(StrictModel):
    order: PositiveInteger
    session_type: Literal["study", "break"]
    duration_minutes: PositiveInteger
    reason: ShortText
    start_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    subject: str | None = None
    topic: str | None = None
    cognitive_demand: str | None = None
    recommended_methods: list[str] = Field(default_factory=list)
    retrieved_record_ids: list[str] = Field(default_factory=list)
    used_fallback: bool = False


class ScheduledSubjectSchema(StrictModel):
    subject: SubjectName
    canonical_subject: str | None
    score: float
    allocated_study_minutes: PositiveInteger
    session_count: PositiveInteger
    reason: ShortText
    retrieved_record_ids: list[str] = Field(default_factory=list)
    used_fallback: bool = False


class UnscheduledSubjectSchema(StrictModel):
    subject: SubjectName
    score: float
    reason: ShortText


class DailyStudyPlanSchema(StrictModel):
    plan_id: ShortText
    total_available_minutes: PositiveInteger
    total_study_minutes: NonNegativeInteger
    total_break_minutes: NonNegativeInteger
    total_planned_minutes: NonNegativeInteger
    unallocated_minutes: NonNegativeInteger
    scheduled_subjects: list[ScheduledSubjectSchema]
    unscheduled_subjects: list[UnscheduledSubjectSchema]
    sessions: list[PlannedSessionSchema]
    warnings: list[str]
    planner_version: ShortText

    @model_validator(mode="after")
    def validate_plan_totals_and_orders(self) -> "DailyStudyPlanSchema":
        orders = [item.order for item in self.sessions]
        if orders != list(range(1, len(orders) + 1)):
            raise ValueError("plan session orders must be consecutive and start at 1")
        study = sum(
            item.duration_minutes for item in self.sessions if item.session_type == "study"
        )
        breaks = sum(
            item.duration_minutes for item in self.sessions if item.session_type == "break"
        )
        if study != self.total_study_minutes or breaks != self.total_break_minutes:
            raise ValueError("plan session durations must match the reported study and break totals")
        if self.total_planned_minutes != study + breaks:
            raise ValueError("total_planned_minutes must equal study plus break minutes")
        if self.unallocated_minutes != self.total_available_minutes - self.total_planned_minutes:
            raise ValueError("unallocated_minutes must match the available time remainder")
        if sum(item.allocated_study_minutes for item in self.scheduled_subjects) != study:
            raise ValueError("scheduled subject allocations must equal total_study_minutes")
        return self


class SensorObservationSchema(StrictModel):
    sensor_enabled: bool
    connection_status: Literal["connected", "disconnected", "unknown"] | None = None
    observation_status: Literal["valid", "missing", "stale", "invalid", "unknown"] | None = None
    continuous_sitting_minutes: NonNegativeInteger | None = None
    poor_posture_duration_minutes: NonNegativeInteger | None = None
    posture_direction: Literal[
        "upright", "leaning_left", "leaning_right", "leaning_forward", "leaning_backward", "unknown"
    ] | None = None
    pressure_imbalance_detected: bool | None = None
    reading_age_seconds: NonNegativeInteger | None = None
    current_session_order: PositiveInteger | None = None
    elapsed_session_minutes: NonNegativeInteger | None = None
    minutes_since_last_reminder: NonNegativeInteger | None = None


class AdaptationActionSchema(StrictModel):
    action: ShortText
    reason: str | None = None
    duration_minutes: PositiveInteger | None = None
    minutes_reduced: PositiveInteger | None = None
    session_order: PositiveInteger | None = None


class AdaptedStudyPlanSchema(StrictModel):
    original_plan_id: ShortText
    adapted_plan_id: ShortText
    adaptation_applied: bool
    mode: str
    severity: str
    triggers: list[str]
    actions: list[AdaptationActionSchema]
    sessions: list[PlannedSessionSchema]
    total_available_minutes: PositiveInteger
    total_study_minutes: NonNegativeInteger
    total_break_minutes: NonNegativeInteger
    total_planned_minutes: NonNegativeInteger
    unallocated_minutes: NonNegativeInteger
    deferred_study_minutes: NonNegativeInteger
    sensor_notice: ShortText
    warnings: list[str]
    sensor_policy_version: ShortText

    @model_validator(mode="after")
    def validate_adapted_totals_and_orders(self) -> "AdaptedStudyPlanSchema":
        orders = [item.order for item in self.sessions]
        if orders != list(range(1, len(orders) + 1)):
            raise ValueError("adapted session orders must be consecutive and start at 1")
        study = sum(
            item.duration_minutes for item in self.sessions if item.session_type == "study"
        )
        breaks = sum(
            item.duration_minutes for item in self.sessions if item.session_type == "break"
        )
        if (study, breaks) != (self.total_study_minutes, self.total_break_minutes):
            raise ValueError("adapted session durations must match the reported totals")
        if self.total_planned_minutes != study + breaks:
            raise ValueError("adapted total_planned_minutes must equal study plus break minutes")
        if self.unallocated_minutes != self.total_available_minutes - self.total_planned_minutes:
            raise ValueError("adapted unallocated_minutes must match the available time remainder")
        return self


class FallbackInformation(StrictModel):
    used: bool
    reason_codes: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)


class PlanResponse(StrictModel):
    plan: DailyStudyPlanSchema
    request_id: str
    processing_time_ms: float
    fallback: FallbackInformation
    api_version: str = API_VERSION


class AdaptPlanRequest(StrictModel):
    plan: DailyStudyPlanSchema
    sensor_observation: SensorObservationSchema | None = None


class AdaptPlanResponse(StrictModel):
    adapted_plan: AdaptedStudyPlanSchema
    request_id: str
    processing_time_ms: float
    api_version: str = API_VERSION


class FullPlanRequest(PlanRequest):
    sensor_observation: SensorObservationSchema | None = None


class FullPlanResponse(StrictModel):
    original_plan: DailyStudyPlanSchema
    adapted_plan: AdaptedStudyPlanSchema | None
    final_sessions: list[PlannedSessionSchema]
    request_id: str
    processing_time_ms: float
    fallback: FallbackInformation
    api_version: str = API_VERSION


class AllocationExplanationSchema(StrictModel):
    subject: str
    allocated_minutes: PositiveInteger
    reason: str


class SessionMessageSchema(StrictModel):
    session_order: PositiveInteger
    message: str


class GroundedResponseSchema(StrictModel):
    summary: str
    allocation_explanations: list[AllocationExplanationSchema]
    session_messages: list[SessionMessageSchema]
    sensor_message: str | None
    unscheduled_message: str | None
    warnings: list[str]


class ExplanationRequest(StrictModel):
    plan: DailyStudyPlanSchema
    adapted_plan: AdaptedStudyPlanSchema | None = None
    timeout_seconds: Annotated[int, Field(strict=True, ge=1, le=120)] | None = None

    @model_validator(mode="after")
    def match_original_and_adapted_plan(self) -> "ExplanationRequest":
        if self.adapted_plan is not None and (
            self.adapted_plan.original_plan_id != self.plan.plan_id
            or self.adapted_plan.total_available_minutes != self.plan.total_available_minutes
        ):
            raise ValueError("adapted_plan must belong to the supplied deterministic plan")
        return self


class ExplanationResponse(StrictModel):
    grounded_response: GroundedResponseSchema
    generation_mode: Literal["local_llm", "local_llm_corrected", "deterministic_fallback"]
    model_status: Literal["available", "unavailable", "timed_out", "invalid_output", "failed"]
    validation_status: Literal["valid", "corrected_valid", "fallback_valid"]
    fallback_reason_code: str | None
    attempt_count: NonNegativeInteger
    generation_latency_ms: float
    request_id: str
    api_version: str = API_VERSION


class FullWithExplanationRequest(FullPlanRequest):
    explanation_timeout_seconds: Annotated[int, Field(strict=True, ge=1, le=120)] | None = None


class FullWithExplanationResponse(StrictModel):
    original_plan: DailyStudyPlanSchema
    adapted_plan: AdaptedStudyPlanSchema | None
    explanation: ExplanationResponse
    request_id: str
    processing_time_ms: float
    fallback: FallbackInformation
    api_version: str = API_VERSION


class ComponentStatus(StrictModel):
    status: Literal["ready", "unavailable", "not_checked"]
    detail: str


class HealthResponse(StrictModel):
    status: Literal["ok"]
    api_version: str
    request_id: str


class ReadinessResponse(StrictModel):
    ready: bool
    components: dict[str, ComponentStatus]
    ollama: ComponentStatus
    api_version: str
    request_id: str


class ErrorDetail(StrictModel):
    field: str | None = None
    message: str


class ErrorBody(StrictModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(StrictModel):
    error: ErrorBody
    request_id: str

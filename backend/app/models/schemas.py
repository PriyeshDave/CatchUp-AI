"""
Pydantic models shared across the API layer.
Keeping these in one place makes the API contract easy to audit and keeps
FastAPI's auto-generated OpenAPI docs (/docs) accurate for the demo.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field


# ---------- Auth ----------

class LoginRequest(BaseModel):
    persona_id: str


class LoginResponse(BaseModel):
    session_token: str
    persona_id: str
    name: str
    role: str
    avatar_color: str


# ---------- Meeting search ----------

class MeetingSearchResult(BaseModel):
    id: str
    title: str
    organizer_name: str
    date: str
    start_time: str
    end_time: str
    platform: str
    sensitivity_label: str


class MeetingSearchResponse(BaseModel):
    query: str
    results: list[MeetingSearchResult]
    result_count: int


# ---------- Transcript ----------

class TranscriptSegment(BaseModel):
    time: str
    speaker: str
    text: str


class TranscriptResponse(BaseModel):
    meeting_id: str
    source: str
    segments: list[TranscriptSegment]


# ---------- Pipeline / orchestration ----------

PipelineStepName = Literal[
    "security_check",
    "read_notes",
    "extract_decisions",
    "find_actions",
    "identify_risks",
    "prioritise_focus",
    "draft_followup",
    "chat_qa",
]

StepStatus = Literal["pending", "running", "done", "error"]


class RunPipelineRequest(BaseModel):
    meeting_id: str


class LLMCallTelemetry(BaseModel):
    step: PipelineStepName
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float
    langsmith_trace_url: Optional[str] = None
    langsmith_enabled: bool = False


class SecurityCheckResult(BaseModel):
    persona_id: str
    persona_name: str
    meeting_id: str
    decision: Literal["ALLOWED", "DENIED"]
    reason: str
    sensitivity_label: Optional[str] = None


class PipelineStepEvent(BaseModel):
    step: PipelineStepName
    status: StepStatus
    label: str
    output: Optional[dict | list | str] = None
    telemetry: Optional[LLMCallTelemetry] = None
    security: Optional[SecurityCheckResult] = None
    error: Optional[str] = None


class RunSummary(BaseModel):
    meeting_id: str
    total_latency_ms: int
    total_wall_clock_ms: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost_usd: float
    langsmith_enabled: bool
    langsmith_project: Optional[str] = None


class RunLogResponse(BaseModel):
    meeting_id: str
    security: SecurityCheckResult
    steps: list[PipelineStepEvent]
    summary: RunSummary


# ---------- Chat ----------

class ChatRequest(BaseModel):
    meeting_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    telemetry: LLMCallTelemetry


# ---------- Follow-up send (mock) ----------

class SendFollowupRequest(BaseModel):
    meeting_id: str
    message: str


class SendFollowupResponse(BaseModel):
    status: str
    sent_to: list[str]

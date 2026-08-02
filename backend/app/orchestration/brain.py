"""
The orchestration "brain".

This is a single, deterministic 6-step pipeline (no multi-agent framework,
no MCP). Each step:
  1. Loads its own prompt template from app/prompts/
  2. Injects the outputs of ALL prior steps as context
  3. Calls the LLM once (via services.openai_client)
  4. Parses the result (JSON for structured steps, plain text for the notes step)
  5. Emits a PipelineStepEvent (used both to build the final result AND to
     drive the live SSE stream consumed by the frontend's pipeline strip and
     System Flow page)

Because each step explicitly receives prior steps' outputs, the model is
reasoning over an accumulating context - e.g. the risk step "sees" the
decisions and actions already extracted, and the prioritisation step "sees"
the risks - which is the "chain of reasoning" requested, without needing an
agent framework to achieve it.
"""
import json
import time
from pathlib import Path
from typing import AsyncGenerator

from app.auth import mock_auth
from app.models.schemas import PipelineStepEvent, RunLogResponse, RunSummary, SecurityCheckResult
from app.orchestration import state as run_state
from app.orchestration.telemetry import build_telemetry, langsmith_project_url, wrap_traceable
from app.services.openai_client import call_llm

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

STEP_LABELS = {
    "security_check": "Checking access & eligibility",
    "read_notes": "Reading notes",
    "extract_decisions": "Extracting decisions",
    "find_actions": "Finding actions",
    "identify_risks": "Identifying risks",
    "prioritise_focus": "Prioritising focus",
    "draft_followup": "Drafting follow-up",
}

SYSTEM_PROMPT = (
    "You are a precise, factual meeting-analysis assistant for a regulated "
    "financial services company. You never invent facts not present in the "
    "provided context. When asked for JSON, you return ONLY valid JSON with "
    "no markdown code fences and no extra commentary."
)


def _load_prompt(name: str) -> str:
    with open(PROMPTS_DIR / f"{name}.txt", "r", encoding="utf-8") as f:
        return f.read()


def _safe_json_parse(text: str, fallback_key: str) -> dict | list:
    """
    Best-effort JSON parsing of an LLM response. Strips accidental markdown
    fences if the model adds them despite instructions, and falls back to a
    minimal structure so a single formatting hiccup doesn't crash the whole
    demo pipeline.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {fallback_key: [], "_parse_warning": "Model output could not be parsed as JSON."}


def _run_llm_step(step_name: str, user_prompt: str):
    """Runs a single LLM call for a step, optionally traced by LangSmith."""

    def _inner():
        return call_llm(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

    traced = wrap_traceable(name=step_name, fn=_inner)
    return traced()


async def run_pipeline(meeting_id: str, persona_id: str) -> AsyncGenerator[PipelineStepEvent, None]:
    """
    The core orchestrated flow. An async generator so the API layer can
    stream each step to the frontend as it completes (SSE), while also
    accumulating a full RunLogResponse for later retrieval / System Flow replay.
    """
    wall_clock_start = time.perf_counter()
    events: list[PipelineStepEvent] = []

    # ---- Step 0: security check (always runs first, gates everything else) ----
    security = mock_auth.check_eligibility(persona_id, meeting_id)
    sec_event = PipelineStepEvent(
        step="security_check",
        status="done" if security.decision == "ALLOWED" else "error",
        label=STEP_LABELS["security_check"],
        security=security,
        error=None if security.decision == "ALLOWED" else security.reason,
    )
    events.append(sec_event)
    yield sec_event

    if security.decision != "ALLOWED":
        summary = RunSummary(
            meeting_id=meeting_id,
            total_latency_ms=0,
            total_wall_clock_ms=int((time.perf_counter() - wall_clock_start) * 1000),
            total_prompt_tokens=0,
            total_completion_tokens=0,
            total_tokens=0,
            total_cost_usd=0.0,
            langsmith_enabled=False,
            langsmith_project=None,
        )
        run_state.save_run(meeting_id, RunLogResponse(meeting_id=meeting_id, security=security, steps=events, summary=summary))
        return

    meeting = mock_auth.get_meeting(meeting_id)
    organizer = mock_auth.get_persona(meeting["organizer"])
    organizer_name = organizer["name"] if organizer else meeting["organizer"]

    transcripts_path = PROMPTS_DIR.parent / "data" / "transcripts.json"
    with open(transcripts_path, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)[meeting_id]
    transcript_text = "\n".join(f"[{seg['time']}] {seg['speaker']}: {seg['text']}" for seg in transcript_data["segments"])

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_latency_ms = 0
    total_cost = 0.0

    def _emit_running(step: str) -> PipelineStepEvent:
        return PipelineStepEvent(step=step, status="running", label=STEP_LABELS[step])  # type: ignore[arg-type]

    # ---- Step 1: read_notes ----
    yield _emit_running("read_notes")
    prompt = _load_prompt("read_notes").format(
        meeting_title=meeting["title"], meeting_date=meeting["date"], transcript=transcript_text
    )
    result = _run_llm_step("read_notes", prompt)
    normalized_notes = result.text
    telem = build_telemetry("read_notes", result)
    total_prompt_tokens += telem.prompt_tokens
    total_completion_tokens += telem.completion_tokens
    total_latency_ms += telem.latency_ms
    total_cost += telem.cost_usd
    ev = PipelineStepEvent(step="read_notes", status="done", label=STEP_LABELS["read_notes"], output=normalized_notes, telemetry=telem)
    events.append(ev)
    yield ev

    # ---- Step 2: extract_decisions ----
    yield _emit_running("extract_decisions")
    prompt = _load_prompt("extract_decisions").format(normalized_notes=normalized_notes)
    result = _run_llm_step("extract_decisions", prompt)
    decisions_obj = _safe_json_parse(result.text, "decisions")
    telem = build_telemetry("extract_decisions", result)
    total_prompt_tokens += telem.prompt_tokens
    total_completion_tokens += telem.completion_tokens
    total_latency_ms += telem.latency_ms
    total_cost += telem.cost_usd
    ev = PipelineStepEvent(step="extract_decisions", status="done", label=STEP_LABELS["extract_decisions"], output=decisions_obj, telemetry=telem)
    events.append(ev)
    yield ev

    # ---- Step 3: find_actions ----
    yield _emit_running("find_actions")
    prompt = _load_prompt("find_actions").format(
        normalized_notes=normalized_notes, decisions_json=json.dumps(decisions_obj)
    )
    result = _run_llm_step("find_actions", prompt)
    actions_obj = _safe_json_parse(result.text, "actions")
    telem = build_telemetry("find_actions", result)
    total_prompt_tokens += telem.prompt_tokens
    total_completion_tokens += telem.completion_tokens
    total_latency_ms += telem.latency_ms
    total_cost += telem.cost_usd
    ev = PipelineStepEvent(step="find_actions", status="done", label=STEP_LABELS["find_actions"], output=actions_obj, telemetry=telem)
    events.append(ev)
    yield ev

    # ---- Step 4: identify_risks ----
    yield _emit_running("identify_risks")
    prompt = _load_prompt("identify_risks").format(
        normalized_notes=normalized_notes,
        decisions_json=json.dumps(decisions_obj),
        actions_json=json.dumps(actions_obj),
    )
    result = _run_llm_step("identify_risks", prompt)
    risks_obj = _safe_json_parse(result.text, "risks")
    telem = build_telemetry("identify_risks", result)
    total_prompt_tokens += telem.prompt_tokens
    total_completion_tokens += telem.completion_tokens
    total_latency_ms += telem.latency_ms
    total_cost += telem.cost_usd
    ev = PipelineStepEvent(step="identify_risks", status="done", label=STEP_LABELS["identify_risks"], output=risks_obj, telemetry=telem)
    events.append(ev)
    yield ev

    # ---- Step 5: prioritise_focus ----
    yield _emit_running("prioritise_focus")
    prompt = _load_prompt("prioritise_focus").format(
        decisions_json=json.dumps(decisions_obj),
        actions_json=json.dumps(actions_obj),
        risks_json=json.dumps(risks_obj),
    )
    result = _run_llm_step("prioritise_focus", prompt)
    priorities_obj = _safe_json_parse(result.text, "priorities")
    telem = build_telemetry("prioritise_focus", result)
    total_prompt_tokens += telem.prompt_tokens
    total_completion_tokens += telem.completion_tokens
    total_latency_ms += telem.latency_ms
    total_cost += telem.cost_usd
    ev = PipelineStepEvent(step="prioritise_focus", status="done", label=STEP_LABELS["prioritise_focus"], output=priorities_obj, telemetry=telem)
    events.append(ev)
    yield ev

    # ---- Step 6: draft_followup ----
    yield _emit_running("draft_followup")
    prompt = _load_prompt("draft_followup").format(
        meeting_title=meeting["title"],
        organizer_name=organizer_name,
        decisions_json=json.dumps(decisions_obj),
        actions_json=json.dumps(actions_obj),
        risks_json=json.dumps(risks_obj),
        priorities_json=json.dumps(priorities_obj),
    )
    result = _run_llm_step("draft_followup", prompt)
    followup_obj = _safe_json_parse(result.text, "body")
    telem = build_telemetry("draft_followup", result)
    total_prompt_tokens += telem.prompt_tokens
    total_completion_tokens += telem.completion_tokens
    total_latency_ms += telem.latency_ms
    total_cost += telem.cost_usd
    ev = PipelineStepEvent(step="draft_followup", status="done", label=STEP_LABELS["draft_followup"], output=followup_obj, telemetry=telem)
    events.append(ev)
    yield ev

    # ---- Final summary + persistence for System Flow replay ----
    wall_clock_ms = int((time.perf_counter() - wall_clock_start) * 1000)
    summary = RunSummary(
        meeting_id=meeting_id,
        total_latency_ms=total_latency_ms,
        total_wall_clock_ms=wall_clock_ms,
        total_prompt_tokens=total_prompt_tokens,
        total_completion_tokens=total_completion_tokens,
        total_tokens=total_prompt_tokens + total_completion_tokens,
        total_cost_usd=round(total_cost, 6),
        langsmith_enabled=events[-1].telemetry.langsmith_enabled if events[-1].telemetry else False,
        langsmith_project=langsmith_project_url(),
    )
    run_state.save_run(meeting_id, RunLogResponse(meeting_id=meeting_id, security=security, steps=events, summary=summary))

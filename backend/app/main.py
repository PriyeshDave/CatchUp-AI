"""
FastAPI application entrypoint.

Routes are intentionally flat and thin - all real logic lives in
app.auth.mock_auth (eligibility) and app.orchestration.brain (the reasoning
pipeline). This keeps the API layer easy to read for a mixed tech/non-tech
demo audience poking at /docs.
"""
import json
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.auth import mock_auth
from app.config import get_settings
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    LoginRequest,
    LoginResponse,
    MeetingSearchResponse,
    MeetingSearchResult,
    RunLogResponse,
    RunPipelineRequest,
    SendFollowupRequest,
    SendFollowupResponse,
    TranscriptResponse,
)
from app.orchestration import brain
from app.orchestration import state as run_state
from app.orchestration.telemetry import build_telemetry
from app.services.openai_client import call_llm

settings = get_settings()

app = FastAPI(
    title="Amex Meeting Catch-Up Assistant (Demo)",
    description="Single-agent orchestrated meeting catch-up assistant, simulating an M365 Copilot experience.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent / "data"


def _persona_from_header(x_session_token: str | None) -> str:
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Missing session token. Please log in.")
    persona_id = mock_auth.resolve_session(x_session_token)
    if not persona_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please log in again.")
    return persona_id


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "env": settings.app_env, "model": settings.openai_model, "langsmith_enabled": settings.langsmith_enabled}


# ---------------------------------------------------------------------------
# Auth (mock persona login)
# ---------------------------------------------------------------------------

@app.get("/api/personas")
def personas():
    """Returns the persona list for the login picker (public - no secrets)."""
    return {"personas": mock_auth.list_personas()}


@app.post("/api/login", response_model=LoginResponse)
def login(req: LoginRequest):
    persona = mock_auth.get_persona(req.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Unknown persona.")
    token = mock_auth.create_session(persona["id"])
    return LoginResponse(
        session_token=token,
        persona_id=persona["id"],
        name=persona["name"],
        role=persona["role"],
        avatar_color=persona["avatar_color"],
    )


# ---------------------------------------------------------------------------
# Meeting search (eligibility-checked)
# ---------------------------------------------------------------------------

@app.get("/api/meetings/search", response_model=MeetingSearchResponse)
def search_meetings(query: str = "", x_session_token: str | None = Header(default=None)):
    persona_id = _persona_from_header(x_session_token)
    matches = mock_auth.search_meetings(query, persona_id)

    results = []
    for m in matches:
        organizer = mock_auth.get_persona(m["organizer"])
        results.append(
            MeetingSearchResult(
                id=m["id"],
                title=m["title"],
                organizer_name=organizer["name"] if organizer else m["organizer"],
                date=m["date"],
                start_time=m["start_time"],
                end_time=m["end_time"],
                platform=m["platform"],
                sensitivity_label=m["sensitivity_label"],
            )
        )
    return MeetingSearchResponse(query=query, results=results, result_count=len(results))


@app.get("/api/meetings/{meeting_id}", response_model=MeetingSearchResult)
def get_meeting_detail(meeting_id: str, x_session_token: str | None = Header(default=None)):
    persona_id = _persona_from_header(x_session_token)
    security = mock_auth.check_eligibility(persona_id, meeting_id)
    if security.decision != "ALLOWED":
        raise HTTPException(status_code=404, detail="No meeting found matching that request.")

    meeting = mock_auth.get_meeting(meeting_id)
    organizer = mock_auth.get_persona(meeting["organizer"])
    return MeetingSearchResult(
        id=meeting["id"],
        title=meeting["title"],
        organizer_name=organizer["name"] if organizer else meeting["organizer"],
        date=meeting["date"],
        start_time=meeting["start_time"],
        end_time=meeting["end_time"],
        platform=meeting["platform"],
        sensitivity_label=meeting["sensitivity_label"],
    )


# ---------------------------------------------------------------------------
# Transcript (eligibility re-checked server-side)
# ---------------------------------------------------------------------------

@app.get("/api/meetings/{meeting_id}/transcript", response_model=TranscriptResponse)
def get_transcript(meeting_id: str, x_session_token: str | None = Header(default=None)):
    persona_id = _persona_from_header(x_session_token)
    security = mock_auth.check_eligibility(persona_id, meeting_id)
    if security.decision != "ALLOWED":
        raise HTTPException(status_code=404, detail="No meeting found matching that request.")

    with open(DATA_DIR / "transcripts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    t = data.get(meeting_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transcript not found.")
    return TranscriptResponse(meeting_id=meeting_id, source=t["source"], segments=t["segments"])


# ---------------------------------------------------------------------------
# Pipeline run - streamed via Server-Sent Events
# ---------------------------------------------------------------------------

@app.get("/api/meetings/{meeting_id}/run-pipeline-stream")
async def run_pipeline_stream(meeting_id: str, x_session_token: str | None = None):
    """
    SSE endpoint. Note: EventSource (browser native) cannot set custom headers,
    so the session token is passed as a query param here specifically for this
    streaming endpoint. It is still validated server-side like every other call.
    """
    persona_id = _persona_from_header(x_session_token)

    async def event_generator():
        async for event in brain.run_pipeline(meeting_id, persona_id):
            yield {"event": "step", "data": event.model_dump_json()}
        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_generator())


@app.get("/api/meetings/{meeting_id}/run-log", response_model=RunLogResponse)
def get_run_log(meeting_id: str, x_session_token: str | None = Header(default=None)):
    """Fetches the most recently completed run's full telemetry (for System Flow page)."""
    persona_id = _persona_from_header(x_session_token)
    security = mock_auth.check_eligibility(persona_id, meeting_id)
    if security.decision != "ALLOWED":
        raise HTTPException(status_code=404, detail="No meeting found matching that request.")

    last_run = run_state.get_last_run(meeting_id)
    if not last_run:
        raise HTTPException(status_code=404, detail="No pipeline run has been executed for this meeting yet.")
    return last_run


# ---------------------------------------------------------------------------
# Ad-hoc chat Q&A over the meeting context
# ---------------------------------------------------------------------------

@app.post("/api/meetings/{meeting_id}/chat", response_model=ChatResponse)
def chat(meeting_id: str, req: ChatRequest, x_session_token: str | None = Header(default=None)):
    persona_id = _persona_from_header(x_session_token)
    security = mock_auth.check_eligibility(persona_id, meeting_id)
    if security.decision != "ALLOWED":
        raise HTTPException(status_code=404, detail="No meeting found matching that request.")

    last_run = run_state.get_last_run(meeting_id)
    if last_run:
        context_parts = []
        for step in last_run.steps:
            if step.output is not None:
                context_parts.append(f"[{step.step}]\n{json.dumps(step.output) if not isinstance(step.output, str) else step.output}")
        context = "\n\n".join(context_parts)
    else:
        # Fall back to raw transcript if the pipeline hasn't been run yet.
        with open(DATA_DIR / "transcripts.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        t = data.get(meeting_id, {"segments": []})
        context = "\n".join(f"[{s['time']}] {s['speaker']}: {s['text']}" for s in t["segments"])

    prompts_dir = Path(__file__).resolve().parent / "prompts"
    with open(prompts_dir / "chat_qa.txt", "r", encoding="utf-8") as f:
        template = f.read()
    prompt = template.format(context=context, question=req.message)

    result = call_llm(
        system_prompt="You are a precise, factual assistant. Answer only from the given context.",
        user_prompt=prompt,
    )
    telem = build_telemetry("chat_qa", result)
    return ChatResponse(reply=result.text, telemetry=telem)


# ---------------------------------------------------------------------------
# Mock "send" of the drafted follow-up
# ---------------------------------------------------------------------------

@app.post("/api/meetings/{meeting_id}/followup/send", response_model=SendFollowupResponse)
def send_followup(meeting_id: str, req: SendFollowupRequest, x_session_token: str | None = Header(default=None)):
    persona_id = _persona_from_header(x_session_token)
    security = mock_auth.check_eligibility(persona_id, meeting_id)
    if security.decision != "ALLOWED":
        raise HTTPException(status_code=404, detail="No meeting found matching that request.")

    meeting = mock_auth.get_meeting(meeting_id)
    recipients = []
    for pid in meeting["eligible_attendees"]:
        p = mock_auth.get_persona(pid)
        if p:
            recipients.append(p["email"])

    # Mock only - no real email is sent in this demo.
    return SendFollowupResponse(status="sent (simulated)", sent_to=recipients)

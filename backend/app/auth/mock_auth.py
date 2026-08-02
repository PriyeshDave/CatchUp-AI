"""
Mock authentication + eligibility (ACL) layer.

This simulates what, in the real M365 Copilot world, would be handled by
Entra ID (auth) + Microsoft Graph (meeting attendee list, sensitivity
labels, sharing permissions). For this demo we keep it simple and file
based, but the *shape* of the check - "is this user allowed to see this
specific meeting's content" - is the real pattern we want to demonstrate.

Important design choice: an ineligible user gets an EMPTY result, not an
explicit "access denied" for the search endpoint. This avoids confirming
that a meeting they can't see even exists, which mirrors real enterprise
search behavior. We only surface the explicit DENIED reason on the
Security panel (System Flow page) for demo/education purposes, not to the
end-user-facing search UI.
"""
import json
import secrets
from pathlib import Path
from typing import Optional

from app.models.schemas import SecurityCheckResult

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_users_cache: Optional[dict] = None
_meetings_cache: Optional[dict] = None

# In-memory session store for the demo (no real auth/session infra needed).
_sessions: dict[str, str] = {}  # session_token -> persona_id


def _load_users() -> dict:
    global _users_cache
    if _users_cache is None:
        with open(DATA_DIR / "users.json", "r", encoding="utf-8") as f:
            _users_cache = json.load(f)
    return _users_cache


def _load_meetings() -> dict:
    global _meetings_cache
    if _meetings_cache is None:
        with open(DATA_DIR / "meetings.json", "r", encoding="utf-8") as f:
            _meetings_cache = json.load(f)
    return _meetings_cache


def get_persona(persona_id: str) -> Optional[dict]:
    for p in _load_users()["personas"]:
        if p["id"] == persona_id:
            return p
    return None


def list_personas() -> list[dict]:
    return _load_users()["personas"]


def create_session(persona_id: str) -> str:
    token = secrets.token_urlsafe(24)
    _sessions[token] = persona_id
    return token


def resolve_session(session_token: str) -> Optional[str]:
    """Returns persona_id for a valid session token, else None."""
    return _sessions.get(session_token)


def get_meeting(meeting_id: str) -> Optional[dict]:
    for m in _load_meetings()["meetings"]:
        if m["id"] == meeting_id:
            return m
    return None


def list_meetings() -> list[dict]:
    return _load_meetings()["meetings"]


def search_meetings(query: str, persona_id: str) -> list[dict]:
    """
    Returns meetings that both (a) match the search query and (b) the
    persona is eligible to see. Ineligible matches are silently dropped -
    this is the enterprise-search-safe pattern.
    """
    query_lower = (query or "").lower().strip()
    results = []
    for m in list_meetings():
        haystack = " ".join([m["title"].lower(), *[k.lower() for k in m["keywords"]]])
        matches_query = (not query_lower) or (query_lower in haystack) or any(
            token in haystack for token in query_lower.split()
        )
        if matches_query and persona_id in m["eligible_attendees"]:
            results.append(m)
    return results


def check_eligibility(persona_id: str, meeting_id: str) -> SecurityCheckResult:
    """
    The core security check reused by every content-bearing endpoint
    (transcript, run-pipeline, chat). This is intentionally re-checked
    server-side on every call - never trust a prior search result or the
    frontend's own state.
    """
    persona = get_persona(persona_id)
    meeting = get_meeting(meeting_id)

    persona_name = persona["name"] if persona else persona_id

    if not persona:
        return SecurityCheckResult(
            persona_id=persona_id,
            persona_name=persona_id,
            meeting_id=meeting_id,
            decision="DENIED",
            reason="Unknown persona / session not recognized.",
        )

    if not meeting:
        return SecurityCheckResult(
            persona_id=persona_id,
            persona_name=persona_name,
            meeting_id=meeting_id,
            decision="DENIED",
            reason="Meeting not found.",
        )

    if persona_id in meeting["eligible_attendees"]:
        return SecurityCheckResult(
            persona_id=persona_id,
            persona_name=persona_name,
            meeting_id=meeting_id,
            decision="ALLOWED",
            reason=f"{persona_name} is on the attendee list for this meeting.",
            sensitivity_label=meeting.get("sensitivity_label"),
        )

    return SecurityCheckResult(
        persona_id=persona_id,
        persona_name=persona_name,
        meeting_id=meeting_id,
        decision="DENIED",
        reason=(
            f"{persona_name} is not on the attendee list and has no sharing "
            f"permission for this '{meeting.get('sensitivity_label', 'Confidential')}' "
            "labeled meeting."
        ),
        sensitivity_label=meeting.get("sensitivity_label"),
    )

"""
Very small in-memory store for the last pipeline run per meeting, so the
System Flow page (or a late-joining browser tab) can fetch a completed run's
full telemetry via GET /run-log without re-running the pipeline.

This is intentionally not a database - it's demo-scoped, process-local
state. Restarting the backend clears it, which is fine for this use case.
"""
from typing import Optional

from app.models.schemas import RunLogResponse

_last_run_by_meeting: dict[str, RunLogResponse] = {}


def save_run(meeting_id: str, run_log: RunLogResponse) -> None:
    _last_run_by_meeting[meeting_id] = run_log


def get_last_run(meeting_id: str) -> Optional[RunLogResponse]:
    return _last_run_by_meeting.get(meeting_id)

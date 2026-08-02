const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders(sessionToken) {
  return sessionToken ? { "x-session-token": sessionToken } : {};
}

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore parse errors on error body
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  base: API_BASE,

  listPersonas: () => fetch(`${API_BASE}/api/personas`).then(handleResponse),

  login: (personaId) =>
    fetch(`${API_BASE}/api/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ persona_id: personaId }),
    }).then(handleResponse),

  searchMeetings: (query, sessionToken) =>
    fetch(`${API_BASE}/api/meetings/search?query=${encodeURIComponent(query)}`, {
      headers: authHeaders(sessionToken),
    }).then(handleResponse),

  getTranscript: (meetingId, sessionToken) =>
    fetch(`${API_BASE}/api/meetings/${meetingId}/transcript`, {
      headers: authHeaders(sessionToken),
    }).then(handleResponse),

  getMeeting: (meetingId, sessionToken) =>
    fetch(`${API_BASE}/api/meetings/${meetingId}`, {
      headers: authHeaders(sessionToken),
    }).then(handleResponse),

  getRunLog: (meetingId, sessionToken) =>
    fetch(`${API_BASE}/api/meetings/${meetingId}/run-log`, {
      headers: authHeaders(sessionToken),
    }).then(handleResponse),

  chat: (meetingId, message, sessionToken) =>
    fetch(`${API_BASE}/api/meetings/${meetingId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders(sessionToken) },
      body: JSON.stringify({ meeting_id: meetingId, message }),
    }).then(handleResponse),

  sendFollowup: (meetingId, message, sessionToken) =>
    fetch(`${API_BASE}/api/meetings/${meetingId}/followup/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders(sessionToken) },
      body: JSON.stringify({ meeting_id: meetingId, message }),
    }).then(handleResponse),

  /**
   * Opens the SSE stream for the pipeline run. Returns the EventSource so the
   * caller can attach listeners and close() it when done.
   * Session token is passed as a query param here because native EventSource
   * cannot set custom headers - still validated server-side on every call.
   */
  streamPipeline: (meetingId, sessionToken) => {
    const url = `${API_BASE}/api/meetings/${meetingId}/run-pipeline-stream?x_session_token=${encodeURIComponent(
      sessionToken
    )}`;
    return new EventSource(url);
  },
};

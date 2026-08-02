# Amex Meeting Catch-Up Assistant (Demo)

A single-agent, tool-using orchestration demo that simulates an **M365 Copilot-style
"Meeting Catch-Up Assistant"** for a fintech credit risk committee. Built with FastAPI +
OpenAI on the backend and a React/Copilot-styled UI on the frontend, fully containerized
with Docker.

> **Scope note:** This is a demo/prototype meant to prove the reasoning pattern and the
> user experience before building the real thing inside M365 Copilot (Microsoft Graph +
> Teams + Copilot Studio/extensibility). Login, Teams meetings, and ACLs are simulated with
> local fixtures; the LLM reasoning and orchestration logic are real.

---

## 1. Problem Statement

Knowledge workers who miss a meeting, or who need to act on one days later, lose time
piecing together **what was decided, what they're on the hook for, and what could bite the
business if ignored** — by rewatching a recording, scrolling a transcript, or pinging
colleagues. In a regulated financial services setting, this problem is sharper:

- Committee decisions (loan approvals/rejections) must be traceable.
- Compliance and regulatory deadlines (e.g. KYC re-verification before an audit) are easy
  to bury inside a 45-minute discussion.
- Not everyone who *wants* the information is *allowed* to have it — meeting content is
  often confidential/sensitivity-labeled, and a catch-up tool must respect that as strictly
  as a human colleague would.

## 2. Use Case

**Amex** (fictional digital lending fintech) runs a **Weekly Credit Risk & Underwriting
Committee** meeting on Microsoft Teams. The committee approves/rejects SME loans, reviews
portfolio delinquency trends, and tracks regulatory compliance gaps.

- **Eligible attendees** (5 personas): CRO, Regional Credit Manager, Head of Underwriting,
  Compliance Officer, Data Science Lead.
- **One ineligible persona** (Sales Lead, not on the invite) is included specifically to
  demonstrate the access-control boundary: they can sign in, but searching for the meeting
  returns no results, exactly as Microsoft Graph would behave for a real, unshared,
  sensitivity-labeled Teams meeting.

Full seed data (transcript, decisions, risks) lives in `backend/app/data/`.

## 3. Value Proposition

| For | Value |
|---|---|
| Committee members | Seconds, not minutes, to recall decisions/actions/risks after the meeting |
| Compliance | Regulatory/audit-relevant risks (e.g. KYC gaps) are surfaced automatically, not buried in a transcript |
| Risk leadership | Portfolio-level risk (e.g. concentration risk across a new loan + existing delinquency trend) is connected across the conversation, not just transcribed |
| IT/Security | Demonstrates that a Copilot-style agent can be eligibility-aware by construction, not by afterthought |
| Engineering | A clean reference pattern for a single orchestrated LLM pipeline — reusable for other "catch me up on X" workflows |

## 4. Solution Overview

A **6-step orchestrated reasoning pipeline** ("the brain") processes a meeting transcript
end-to-end:

```
security check → read notes → extract decisions → find actions → identify risks → prioritise focus → draft follow-up
```

Each step is one prompt template + one LLM call. Every step after the first receives the
**outputs of all prior steps** as context, so the reasoning chains together (e.g. the risk
step already knows the decisions and actions, so it can flag that a new textile-sector loan
overlaps with a portfolio-level textile delinquency trend).

This is **not** a multi-agent framework and does not use MCP — it's one Python
orchestrator class with a fixed control flow, calling the OpenAI API directly. LangSmith
tracing is available as an **optional** add-on (see below) purely for observability.

### Architecture diagram

```
┌──────────────────────────┐        ┌───────────────────────────────────────────┐
│        React UI          │  HTTP  │                 FastAPI                    │
│ (white, Copilot-styled)  │◄──────►│                                             │
│                          │        │  ┌───────────────┐   ┌───────────────────┐ │
│  - Login (persona)       │  SSE   │  │ mock_auth.py   │   │ orchestration/    │ │
│  - Copilot Home (search) │◄──────►│  │ (ACL + session)│   │   brain.py        │ │
│  - Meeting Workspace     │        │  └───────┬───────┘   │   telemetry.py    │ │
│    (pipeline strip,      │        │          │            │   state.py        │ │
│     tabs, chat rail)     │        │          ▼            └─────────┬─────────┘ │
│  - System Flow           │        │  ┌───────────────┐              │           │
│    (security panel,      │        │  │  data/*.json   │              ▼           │
│     LLM call ledger,     │        │  │ (meetings,     │   ┌───────────────────┐  │
│     run summary)         │        │  │  transcripts,  │   │  services/         │  │
│                          │        │  │  users)        │   │   openai_client.py │  │
└──────────────────────────┘        │  └───────────────┘   └─────────┬─────────┘  │
                                     │                                 │            │
                                     └─────────────────────────────────┼────────────┘
                                                                       ▼
                                                              ┌─────────────────┐
                                                              │   OpenAI API     │
                                                              │ (gpt-4o-mini)    │
                                                              └─────────────────┘
                                                                       │
                                                          (optional)   ▼
                                                              ┌─────────────────┐
                                                              │   LangSmith      │
                                                              │ (trace/cost obs) │
                                                              └─────────────────┘
```

### Access control (the part that makes this feel real)

- Every content-bearing endpoint (transcript, run-pipeline, chat, run-log) **re-checks
  eligibility server-side**, regardless of what the frontend already showed.
- An ineligible search returns an **empty result set**, not an explicit "access denied" —
  this mirrors real enterprise search behavior (never confirm a sensitive meeting exists to
  someone who isn't allowed to see it).
- The **System Flow** page exposes the explicit `ALLOWED` / `DENIED` decision and reason,
  for demo/education purposes — showing the audience the mechanism without exposing it in
  the end-user-facing search UI.

### Observability: System Flow page

A second page (`/meeting/:id/system-flow`) shows, live via Server-Sent Events:

1. **Security check** — persona, decision, reason, sensitivity label.
2. **Data flow graph** — the 6 pipeline nodes lighting up in real time with per-step
   latency, token counts, and cost.
3. **LLM call ledger** — a table, one row per model call, with a LangSmith trace link if
   configured.
4. **Run summary** — total wall-clock time, total tokens, total cost, LangSmith status.

**LangSmith is optional.** If `LANGCHAIN_API_KEY` / `LANGCHAIN_TRACING_V2=true` are set in
`.env`, calls are wrapped with LangSmith's standalone `traceable` decorator (not the
LangChain framework) and trace links appear. If unset, the app computes the same
latency/token/cost telemetry itself and simply shows "Not configured" instead of a trace
link — nothing else changes.

### Cost tracking

`backend/app/data/pricing.json` holds $/1K-token rates per model. Cost is computed per step
from the OpenAI response's real `usage` field, so it reflects actual token counts, not
estimates.

---

## 5. Repository Layout

```
Amex-catchup-demo/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI routes
│   │   ├── config.py                # .env-driven settings
│   │   ├── auth/mock_auth.py        # persona login + eligibility (ACL)
│   │   ├── orchestration/
│   │   │   ├── brain.py             # the 6-step orchestrated pipeline
│   │   │   ├── telemetry.py         # cost calc + optional LangSmith wrapper
│   │   │   └── state.py             # last-run cache (for System Flow replay)
│   │   ├── prompts/*.txt            # one template per pipeline step
│   │   ├── models/schemas.py        # Pydantic request/response models
│   │   ├── services/openai_client.py
│   │   └── data/                    # seed fixtures (meetings, transcripts, users, pricing)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/ (Login, CopilotHome, MeetingWorkspace, SystemFlow)
│   │   ├── components/ (PipelineStrip, PipelineGraph, ChatRail, SecurityPanel,
│   │   │                LLMCallTable, RunSummaryFooter, OutputTabs, AppShell)
│   │   ├── api/client.js
│   │   ├── context/SessionContext.jsx
│   │   └── styles/theme.css
│   ├── package.json
│   ├── Dockerfile
│   ├── nginx.conf
│   └── .env.example
├── docker-compose.yml
├── .env.example
└── README.md   (this file)
```

---

## 6. Engineering Runbook

### Prerequisites

- Docker + Docker Compose (recommended path), **or** Python 3.12 + Node.js 20 for local dev
- An OpenAI API key
- (Optional) A LangSmith API key, if you want real trace links

### Quick start (Docker)

```bash
git clone <this-repo>
cd Amex-catchup-demo

cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...

docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend docs (Swagger): http://localhost:8000/docs

Sign in as any persona except **Karan Mehta** to walk through the full flow. Sign in as
**Karan Mehta** to demonstrate the access-control boundary (search returns no results).

### Local dev (without Docker)

**Backend:**
```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # edit OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
cp .env.example .env               # VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev                        # http://localhost:3000
```

### Enabling LangSmith (optional)

1. Get an API key from https://smith.langchain.com
2. In `.env`:
   ```
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=ls__your-key
   LANGCHAIN_PROJECT=Amex-catchup-demo
   ```
3. Restart the backend. The System Flow page's LLM Call Ledger will now show "View trace ↗"
   links per step, and the Run Summary will link to the LangSmith project dashboard.
4. No key set → app behaves identically, minus the trace links.

### Adding a new pipeline step

1. Add a new `.txt` prompt template in `backend/app/prompts/`.
2. Add the step name to `PipelineStepName` in `backend/app/models/schemas.py`.
3. Add a block in `backend/app/orchestration/brain.py::run_pipeline` following the existing
   pattern (`_emit_running` → load prompt → `_run_llm_step` → `build_telemetry` → emit
   `PipelineStepEvent`).
4. Add the step to `PIPELINE_STEPS` in `frontend/src/components/pipelineSteps.js` — it will
   automatically appear in both the pipeline strip and the System Flow graph.

### Adding a new meeting / persona (seed data)

- New persona: add an entry to `backend/app/data/users.json`.
- New meeting: add an entry to `backend/app/data/meetings.json` (include
  `eligible_attendees` and `keywords` for search matching) and a matching transcript block
  in `backend/app/data/transcripts.json`.
- No code changes needed — the search, ACL, and pipeline all read from these files.

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 Missing session token` | Frontend didn't send `x-session-token` header | Confirm you're logged in; check `SessionContext` is storing the token |
| CORS error in browser console | `CORS_ORIGINS` in `.env` doesn't include the frontend's origin | Add the exact origin (scheme+host+port) to `CORS_ORIGINS` |
| OpenAI 401/403 errors | `OPENAI_API_KEY` missing/invalid | Check `.env`, restart backend container |
| Pipeline stuck on "Running…" | SSE connection dropped or backend crashed | Check `docker logs Amex-catchup-backend`; browser dev tools Network tab for the `run-pipeline-stream` request |
| A step's output looks empty / has `_parse_warning` | Model didn't return valid JSON for that step | Check the step's prompt template — usually a wording tweak fixes it; the pipeline degrades gracefully rather than crashing |
| System Flow page empty on first visit | No run has been executed yet for that meeting | Click "Run live", or run the pipeline first from the Assistant tab |

---

## 7. What's Simulated vs Real

| Component | Real | Simulated |
|---|---|---|
| LLM reasoning (6-step pipeline) | ✅ Real OpenAI calls | |
| Access control logic (ACL check) | ✅ Real check against fixture data | Fixture data itself is seeded, not from real Graph/Teams |
| Latency, token counts, cost | ✅ Computed from real OpenAI API responses | |
| LangSmith tracing | ✅ Real, if configured | |
| Login | | Persona picker, no real Entra ID/OAuth |
| Teams meeting + transcript | | Static JSON fixture, not a live Teams recording |
| "Send follow-up" | | Returns a mocked success, no real email/Teams message is sent |

---

## 8. Path to Production (M365 Copilot)

This demo is designed so the swap-in points are obvious:
- `mock_auth.py` → Microsoft Graph (`/me`, meeting attendee list, sensitivity labels, sharing permissions)
- `transcripts.json` → Microsoft Graph `callTranscripts` / Teams meeting transcript API
- Persona login → Entra ID / SSO
- The orchestration `brain.py` and prompts are provider-agnostic and can be ported into a
  Copilot Studio custom engine agent or an M365 Copilot extensibility plugin largely as-is.

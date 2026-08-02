import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useSession } from "../context/SessionContext.jsx";

const SUGGESTED_QUERIES = [
  "Updates from the standup today",
  "ServiceNow Incident Data Management",
  "Sentiment Analytics Review",
];

export default function CopilotHome() {
  const { session } = useSession();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);
  const [searchedOnce, setSearchedOnce] = useState(false);

  async function runSearch(q) {
    setSearching(true);
    setError(null);
    try {
      const res = await api.searchMeetings(q, session.sessionToken);
      setResults(res.results);
    } catch (e) {
      setError(e.message);
      setResults([]);
    } finally {
      setSearching(false);
      setSearchedOnce(true);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    runSearch(query);
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "auto" }}>
      <div style={{ maxWidth: 720, margin: "0 auto", width: "100%", padding: "72px 24px 40px" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ fontSize: 13, color: "var(--text-tertiary)", marginBottom: 6 }}>
            Signed in as <strong style={{ color: "var(--text-secondary)" }}>{session.name}</strong>
            {" · "}
            {session.role}
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 600, margin: "0 0 8px" }}>
            Ask about a meeting
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 15, margin: 0 }}>
            Search for a Teams meeting to get decisions, actions, risks, and a draft follow-up.
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ marginBottom: 16 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-lg)",
              padding: "6px 8px 6px 18px",
              boxShadow: "var(--shadow-sm)",
              gap: 10,
            }}
          >
            <SearchIcon />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. credit risk committee meeting today"
              style={{
                flex: 1,
                border: "none",
                outline: "none",
                fontSize: 15,
                padding: "10px 0",
                background: "transparent",
                color: "var(--text-primary)",
              }}
            />
            <button
              type="submit"
              disabled={searching}
              style={{
                background: "var(--accent-primary)",
                color: "#fff",
                border: "none",
                borderRadius: "var(--radius-md)",
                padding: "10px 18px",
                fontSize: 14,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {searching ? "Searching…" : "Search"}
            </button>
          </div>
        </form>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 32 }}>
          {SUGGESTED_QUERIES.map((q) => (
            <button
              key={q}
              onClick={() => {
                setQuery(q);
                runSearch(q);
              }}
              style={{
                fontSize: 13,
                border: "1px solid var(--border-default)",
                background: "var(--surface-subtle)",
                borderRadius: 20,
                padding: "6px 12px",
                cursor: "pointer",
                color: "var(--text-secondary)",
              }}
            >
              {q}
            </button>
          ))}
        </div>

        {error && (
          <div
            style={{
              background: "var(--danger-tint)",
              color: "var(--danger)",
              padding: "10px 14px",
              borderRadius: "var(--radius-md)",
              fontSize: 13,
              marginBottom: 16,
            }}
          >
            {error}
          </div>
        )}

        {searchedOnce && !searching && results && results.length === 0 && !error && (
          <div
            style={{
              textAlign: "center",
              padding: "40px 20px",
              border: "1px dashed var(--border-default)",
              borderRadius: "var(--radius-lg)",
              color: "var(--text-secondary)",
            }}
          >
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6, color: "var(--text-primary)" }}>
              No results found
            </div>
            <div style={{ fontSize: 13, maxWidth: 380, margin: "0 auto" }}>
              We couldn't find a meeting matching that search. This may be because the meeting
              doesn't exist, or because it hasn't been shared with you.
            </div>
          </div>
        )}

        {results && results.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {results.map((m) => (
              <button
                key={m.id}
                onClick={() => navigate(`/meeting/${m.id}`)}
                style={{
                  textAlign: "left",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-md)",
                  padding: "16px 18px",
                  background: "var(--surface-card)",
                  cursor: "pointer",
                  boxShadow: "var(--shadow-sm)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{m.title}</div>
                    <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                      {m.platform} · {m.date} · {m.start_time}–{m.end_time} · Organized by {m.organizer_name}
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: "var(--accent-primary)",
                      background: "var(--accent-primary-tint)",
                      padding: "4px 10px",
                      borderRadius: 20,
                      whiteSpace: "nowrap",
                      marginLeft: 12,
                    }}
                  >
                    {m.sensitivity_label}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

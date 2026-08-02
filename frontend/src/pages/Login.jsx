import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useSession } from "../context/SessionContext.jsx";
import { Avatar } from "../components/AppShell.jsx";

export default function Login() {
  const [personas, setPersonas] = useState([]);
  const [loadingId, setLoadingId] = useState(null);
  const [error, setError] = useState(null);
  const { login } = useSession();
  const navigate = useNavigate();

  useEffect(() => {
    api
      .listPersonas()
      .then((res) => setPersonas(res.personas))
      .catch((e) => setError(e.message));
  }, []);

  async function handleLogin(personaId) {
    setLoadingId(personaId);
    setError(null);
    try {
      await login(personaId);
      navigate("/");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <div
      style={{
        height: "100vh",
        width: "100vw",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--surface-canvas)",
      }}
    >
      <div style={{ width: 480, textAlign: "center" }}>
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: "var(--radius-lg)",
            background: "linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))",
            margin: "0 auto 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontWeight: 700,
            fontSize: 24,
          }}
        >
          N
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 600, margin: "0 0 4px" }}>DW Workspace</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 14, margin: "0 0 28px" }}>
          Sign in to continue to Meeting Catch-Up Assistant. This demo simulates Microsoft 365
          sign-in by letting you pick a persona.
        </p>

        {error && (
          <div
            style={{
              background: "var(--danger-tint)",
              color: "var(--danger)",
              padding: "10px 14px",
              borderRadius: "var(--radius-md)",
              fontSize: 13,
              marginBottom: 16,
              textAlign: "left",
            }}
          >
            {error}
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 8, textAlign: "left" }}>
          {personas.map((p) => (
            <button
              key={p.id}
              onClick={() => handleLogin(p.id)}
              disabled={loadingId !== null}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "12px 14px",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-md)",
                background: "var(--surface-card)",
                cursor: loadingId ? "default" : "pointer",
                opacity: loadingId && loadingId !== p.id ? 0.5 : 1,
                transition: "border-color 120ms ease, background 120ms ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--accent-primary)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-default)")}
            >
              <Avatar name={p.name} color={p.avatar_color} avatarUrl={`/avatars/${p.id}.png`} size={36} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{p.name}</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{p.role}</div>
              </div>
              {p.note && (
                <div
                  style={{
                    fontSize: 11,
                    color: "var(--warning)",
                    background: "var(--warning-tint)",
                    padding: "3px 8px",
                    borderRadius: 20,
                    fontWeight: 600,
                    flexShrink: 0,
                  }}
                >
                  Not invited
                </div>
              )}
              {loadingId === p.id && (
                <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Signing in…</div>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

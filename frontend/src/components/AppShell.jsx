import { useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { useSession } from "../context/SessionContext.jsx";

export function Avatar({ name, color, size = 32, avatarUrl }) {
  const initials = name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const [imgFailed, setImgFailed] = useState(false);
  const showImage = avatarUrl && !imgFailed;

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: color,
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 600,
        fontSize: size * 0.38,
        flexShrink: 0,
        overflow: "hidden",
      }}
      title={name}
    >
      {showImage ? (
        <img
          src={avatarUrl}
          alt={name}
          width={size}
          height={size}
          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          onError={() => setImgFailed(true)}
        />
      ) : (
        initials
      )}
    </div>
  );
}

export default function AppShell({ children }) {
  const { session, logout } = useSession();
  const navigate = useNavigate();
  const { meetingId } = useParams();
  const location = useLocation();

  const onSystemFlow = location.pathname.endsWith("/system-flow");
  const inMeeting = !!meetingId;

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw", background: "var(--surface-canvas)" }}>
      {/* Left nav rail */}
      <div
        style={{
          width: "var(--nav-width)",
          borderRight: "1px solid var(--border-default)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "16px 0",
          gap: 20,
          flexShrink: 0,
        }}
      >
        <div
          onClick={() => navigate("/")}
          title="Home"
          style={{
            width: 40,
            height: 40,
            borderRadius: "var(--radius-md)",
            background: "linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontWeight: 700,
            fontSize: 16,
            cursor: "pointer",
          }}
        >
          N
        </div>

        <div style={{ flex: 1 }} />

        {inMeeting && (
          <>
            <NavIcon
              label="Assistant"
              active={!onSystemFlow}
              onClick={() => navigate(`/meeting/${meetingId}`)}
              symbol="C"
            />
            <NavIcon
              label="System Flow"
              active={onSystemFlow}
              onClick={() => navigate(`/meeting/${meetingId}/system-flow`)}
              symbol="F"
            />
          </>
        )}

        <div style={{ flex: 2 }} />

        {session && (
          <div
            onClick={logout}
            title={`${session.name} - sign out`}
            style={{ cursor: "pointer" }}
          >
            <Avatar
              name={session.name}
              color={session.avatarColor}
              avatarUrl={`/avatars/${session.personaId}.png`}
            />
          </div>
        )}
      </div>

      {/* Main column */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {children}
      </div>
    </div>
  );
}

function NavIcon({ label, active, onClick, symbol }) {
  return (
    <button
      onClick={onClick}
      title={label}
      style={{
        width: 40,
        height: 40,
        borderRadius: "var(--radius-md)",
        border: "none",
        background: active ? "var(--accent-primary-tint)" : "transparent",
        color: active ? "var(--accent-primary)" : "var(--text-secondary)",
        fontWeight: 700,
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 14,
      }}
    >
      {symbol}
    </button>
  );
}

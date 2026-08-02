function Card({ children }) {
  return (
    <div
      style={{
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-md)",
        padding: "14px 16px",
        background: "var(--surface-card)",
        marginBottom: 10,
      }}
    >
      {children}
    </div>
  );
}

function EmptyState({ label }) {
  return (
    <div style={{ color: "var(--text-tertiary)", fontSize: 13, padding: "24px 0", textAlign: "center" }}>
      {label}
    </div>
  );
}

export function OverviewTab({ outputs }) {
  const notes = outputs.read_notes;
  const decisions = outputs.extract_decisions?.decisions || [];
  const actions = outputs.find_actions?.actions || [];
  const risks = outputs.identify_risks?.risks || [];

  if (!notes) return <EmptyState label="Run the assistant to see a meeting overview here." />;

  return (
    <div>
      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <StatPill label="Decisions" value={decisions.length} color="var(--step-decisions)" />
        <StatPill label="Actions" value={actions.length} color="var(--step-actions)" />
        <StatPill label="Risks" value={risks.length} color="var(--step-risks)" />
      </div>
      <div style={{ fontSize: 13, lineHeight: 1.8, whiteSpace: "pre-wrap" }}>{notes}</div>
    </div>
  );
}

function StatPill({ label, value, color }) {
  return (
    <div
      style={{
        border: `1px solid ${color}33`,
        background: `${color}10`,
        borderRadius: "var(--radius-md)",
        padding: "8px 14px",
        minWidth: 90,
      }}
    >
      <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11.5, color: "var(--text-secondary)" }}>{label}</div>
    </div>
  );
}

export function TranscriptTab({ transcript }) {
  if (!transcript) return <EmptyState label="Loading transcript…" />;
  return (
    <div>
      <div style={{ fontSize: 11.5, color: "var(--text-tertiary)", marginBottom: 10 }}>
        Source: {transcript.source}
      </div>
      {transcript.segments.map((s, i) => (
        <div key={i} style={{ display: "flex", gap: 12, marginBottom: 10, fontSize: 13 }}>
          <div style={{ color: "var(--text-tertiary)", width: 46, flexShrink: 0 }}>{s.time}</div>
          <div>
            <strong>{s.speaker}:</strong> {s.text}
          </div>
        </div>
      ))}
    </div>
  );
}

export function DecisionsTab({ outputs }) {
  const decisions = outputs.extract_decisions?.decisions;
  if (!decisions) return <EmptyState label="Run the assistant to extract decisions." />;
  if (decisions.length === 0) return <EmptyState label="No decisions were identified in this meeting." />;
  return (
    <div>
      {decisions.map((d, i) => (
        <Card key={i}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--step-decisions)", marginBottom: 4 }}>
            {d.subject}
          </div>
          <div style={{ fontSize: 14, marginBottom: 4 }}>{d.decision}</div>
          <div style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>{d.detail}</div>
        </Card>
      ))}
    </div>
  );
}

export function ActionsTab({ outputs }) {
  const actions = outputs.find_actions?.actions;
  if (!actions) return <EmptyState label="Run the assistant to find action items." />;
  if (actions.length === 0) return <EmptyState label="No action items were identified." />;
  return (
    <div>
      {actions.map((a, i) => (
        <Card key={i}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
            <div style={{ fontSize: 14, fontWeight: 500 }}>{a.task}</div>
            <span
              style={{
                fontSize: 11,
                background: "var(--surface-sunken)",
                padding: "3px 9px",
                borderRadius: 20,
                whiteSpace: "nowrap",
                color: "var(--text-secondary)",
              }}
            >
              {a.due_date}
            </span>
          </div>
          <div style={{ fontSize: 12.5, color: "var(--text-secondary)", marginTop: 4 }}>
            Owner: <strong>{a.owner}</strong> · Related to: {a.related_decision}
          </div>
        </Card>
      ))}
    </div>
  );
}

const SEVERITY_COLOR = { high: "var(--danger)", medium: "var(--warning)", low: "var(--success)" };
const SEVERITY_TINT = { high: "var(--danger-tint)", medium: "var(--warning-tint)", low: "var(--success-tint)" };

export function RisksTab({ outputs }) {
  const risks = outputs.identify_risks?.risks;
  if (!risks) return <EmptyState label="Run the assistant to identify risks." />;
  if (risks.length === 0) return <EmptyState label="No risks were identified." />;
  return (
    <div>
      {risks.map((r, i) => (
        <Card key={i}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{r.title}</div>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: "uppercase",
                color: SEVERITY_COLOR[r.severity] || "var(--text-secondary)",
                background: SEVERITY_TINT[r.severity] || "var(--surface-sunken)",
                padding: "3px 9px",
                borderRadius: 20,
                whiteSpace: "nowrap",
              }}
            >
              {r.severity}
            </span>
          </div>
          <div style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "4px 0" }}>{r.category}</div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{r.detail}</div>
        </Card>
      ))}
    </div>
  );
}

export function PrioritiesTab({ outputs }) {
  const priorities = outputs.prioritise_focus?.priorities;
  if (!priorities) return <EmptyState label="Run the assistant to see prioritised focus areas." />;
  return (
    <div>
      {priorities
        .slice()
        .sort((a, b) => a.rank - b.rank)
        .map((p, i) => (
          <Card key={i}>
            <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
              <div
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: "50%",
                  background: "var(--step-priorities)",
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: 13,
                  flexShrink: 0,
                }}
              >
                {p.rank}
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{p.title}</div>
                <div style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>{p.why}</div>
              </div>
            </div>
          </Card>
        ))}
    </div>
  );
}

export function FollowupTab({ outputs, draft, setDraft, onSend, sendStatus }) {
  const followup = outputs.draft_followup;
  if (!followup) return <EmptyState label="Run the assistant to generate a draft follow-up." />;

  return (
    <div>
      <div style={{ fontSize: 12.5, color: "var(--text-secondary)", marginBottom: 6 }}>Subject</div>
      <div
        style={{
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-md)",
          padding: "9px 12px",
          fontSize: 14,
          fontWeight: 600,
          marginBottom: 14,
          background: "var(--surface-card)",
        }}
      >
        {typeof followup === "string" ? "Recap" : followup.subject}
      </div>

      <div style={{ fontSize: 12.5, color: "var(--text-secondary)", marginBottom: 6 }}>Message (editable)</div>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={10}
        style={{
          width: "100%",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-md)",
          padding: 12,
          fontSize: 13.5,
          lineHeight: 1.6,
          fontFamily: "inherit",
          resize: "vertical",
        }}
      />

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 12 }}>
        <button
          onClick={onSend}
          style={{
            background: "var(--accent-primary)",
            color: "#fff",
            border: "none",
            borderRadius: "var(--radius-md)",
            padding: "9px 18px",
            fontSize: 13.5,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Send follow-up
        </button>
        {sendStatus && <span style={{ fontSize: 12.5, color: "var(--success)" }}>{sendStatus}</span>}
      </div>
    </div>
  );
}

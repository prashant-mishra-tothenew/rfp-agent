import { formatElapsed } from "./Spinner";

const STEP_LABELS: Record<string, string> = {
  writing: "Writing proposal sections",
  render: "Building Word document",
  pptx: "Building PowerPoint deck",
  pdf: "Preparing downloads",
  complete: "Finishing up",
};

const SECTION_GROUPS = [
  "Executive Summary",
  "Solution & Approach",
  "Security & Experience",
];

export function ProposalLoader({
  step,
  percent,
  message,
  elapsedSeconds,
  sectionDone,
  sectionTotal,
}: {
  step?: string;
  percent?: number;
  message?: string;
  elapsedSeconds: number;
  sectionDone?: number;
  sectionTotal?: number;
}) {
  const pct = Math.max(percent ?? 2, 2);
  const stepLabel = step ? STEP_LABELS[step] || step : "Starting";
  const activeGroup =
    sectionTotal && sectionTotal > 0
      ? Math.min(sectionDone ?? 0, sectionTotal - 1)
      : 0;

  return (
    <div
      role="status"
      aria-live="polite"
      className="proposal-loader"
      style={{
        background: "linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 50%, #f8fafc 100%)",
        border: "1px solid #86efac",
        borderRadius: 16,
        padding: "2rem 1.5rem",
        marginBottom: "1.5rem",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div className="proposal-shimmer" aria-hidden="true" />

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "1.5rem",
          flexWrap: "wrap",
          justifyContent: "center",
        }}
      >
        <div className="proposal-ring-wrap" aria-hidden="true">
          <svg className="proposal-ring" viewBox="0 0 120 120">
            <circle className="proposal-ring-bg" cx="60" cy="60" r="52" />
            <circle
              className="proposal-ring-fg"
              cx="60"
              cy="60"
              r="52"
              style={{
                strokeDasharray: `${2 * Math.PI * 52}`,
                strokeDashoffset: `${2 * Math.PI * 52 * (1 - pct / 100)}`,
              }}
            />
          </svg>
          <div className="proposal-ring-label">{pct}%</div>
        </div>

        <div style={{ textAlign: "left", maxWidth: 420 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
            <span className="proposal-doc-icon" aria-hidden="true">📄</span>
            <h3 style={{ margin: 0, color: "#065f46", fontSize: "1.125rem" }}>
              Generating your proposal
            </h3>
          </div>
          <p style={{ margin: "0 0 0.75rem", color: "#047857", fontWeight: 600, fontSize: "0.95rem" }}>
            {stepLabel}
            {sectionTotal && sectionTotal > 0
              ? ` (${sectionDone ?? 0}/${sectionTotal} groups)`
              : ""}
          </p>

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
            {SECTION_GROUPS.map((label, i) => {
              const done = i < activeGroup;
              const current = i === activeGroup;
              return (
                <span
                  key={label}
                  className={`proposal-chip${done ? " done" : ""}${current ? " active" : ""}`}
                >
                  {done ? "✓ " : current ? "● " : ""}
                  {label}
                </span>
              );
            })}
          </div>

          <div
            style={{
              display: "flex",
              gap: "1rem",
              fontSize: "0.8rem",
              color: "#64748b",
              flexWrap: "wrap",
            }}
          >
            <span>Elapsed: {formatElapsed(elapsedSeconds)}</span>
            <span className="pulse-dot">Usually 1–3 min with batched sections</span>
          </div>
        </div>
      </div>

      {message && (
        <p
          style={{
            margin: "1rem 0 0",
            color: "#475569",
            fontSize: "0.875rem",
            textAlign: "center",
          }}
        >
          {message}
        </p>
      )}
    </div>
  );
}

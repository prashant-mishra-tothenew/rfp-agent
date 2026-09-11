import { Spinner, formatElapsed } from "./Spinner";

const STEP_LABELS: Record<string, string> = {
  starting: "Starting",
  analyzer: "Extracting requirements",
  knowledge: "Finding evidence",
  response: "Drafting responses",
  compliance: "Running compliance check",
  complete: "Finishing up",
};

export function PipelineLoader({
  step,
  percent,
  message,
  elapsedSeconds,
  requirementDone,
  requirementTotal,
}: {
  step?: string;
  percent?: number;
  message?: string;
  elapsedSeconds: number;
  requirementDone?: number;
  requirementTotal?: number;
}) {
  const stepLabel = step ? STEP_LABELS[step] || step : "Processing";

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        background: "linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%)",
        border: "1px solid #bfdbfe",
        borderRadius: 12,
        padding: "2rem",
        marginBottom: "1.5rem",
        textAlign: "center",
      }}
    >
      <Spinner size="lg" variant="dark" />
      <h3 style={{ margin: "1rem 0 0.5rem", color: "#0f172a", fontSize: "1.125rem" }}>
        Generating draft responses…
      </h3>
      <p style={{ margin: "0 0 1rem", color: "#2563eb", fontWeight: 600, fontSize: "0.95rem" }}>
        {stepLabel}
        {requirementTotal && requirementTotal > 0 && step !== "analyzer"
          ? ` (${requirementDone ?? 0}/${requirementTotal})`
          : ""}
      </p>

      <div
        style={{
          background: "#e2e8f0",
          borderRadius: 999,
          height: 10,
          overflow: "hidden",
          maxWidth: 480,
          margin: "0 auto 0.75rem",
        }}
      >
        <div
          style={{
            background: "linear-gradient(90deg, #2563eb, #3b82f6)",
            height: "100%",
            width: `${Math.max(percent ?? 2, 2)}%`,
            transition: "width 0.5s ease",
            borderRadius: 999,
          }}
        />
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          gap: "1.5rem",
          fontSize: "0.8rem",
          color: "#64748b",
          flexWrap: "wrap",
        }}
      >
        <span>{percent ?? 0}% complete</span>
        <span>Elapsed: {formatElapsed(elapsedSeconds)}</span>
        <span className="pulse-dot">Usually 4–10 min on local hardware</span>
      </div>

      {message && (
        <p style={{ margin: "1rem 0 0", color: "#475569", fontSize: "0.875rem" }}>
          {message}
        </p>
      )}
    </div>
  );
}

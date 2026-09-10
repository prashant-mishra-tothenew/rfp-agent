const STEPS = [
  { key: "analyzer", label: "Extract Requirements" },
  { key: "knowledge", label: "Find Evidence" },
  { key: "response", label: "Draft Responses" },
  { key: "compliance", label: "Compliance Check" },
  { key: "complete", label: "Ready for Review" },
];

export function PipelineStepper({
  currentStep,
  percent,
  message,
  active,
}: {
  currentStep?: string;
  percent?: number;
  message?: string;
  active: boolean;
}) {
  const stepIndex = STEPS.findIndex((s) => s.key === currentStep);

  return (
    <div
      style={{
        background: "white",
        padding: "1.5rem",
        borderRadius: 12,
        marginBottom: "1.5rem",
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
        }}
      >
        <h3 style={{ margin: 0, fontSize: "1rem" }}>
          {active ? "Analyzing RFP..." : "Pipeline Steps"}
        </h3>
        {active && (
          <span style={{ color: "#2563eb", fontWeight: 600, fontSize: "0.875rem" }}>
            {percent ?? 0}%
          </span>
        )}
      </div>

      {active && (
        <div
          style={{
            background: "#e2e8f0",
            borderRadius: 8,
            height: 8,
            overflow: "hidden",
            marginBottom: "1rem",
          }}
        >
          <div
            style={{
              background: "#2563eb",
              height: "100%",
              width: `${percent ?? 0}%`,
              transition: "width 0.4s ease",
            }}
          />
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${STEPS.length}, 1fr)`,
          gap: "0.5rem",
        }}
      >
        {STEPS.map((step, i) => {
          const done = stepIndex > i || currentStep === "complete";
          const current = step.key === currentStep;
          return (
            <div key={step.key} style={{ textAlign: "center" }}>
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  margin: "0 auto 0.5rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  background: done ? "#16a34a" : current ? "#2563eb" : "#e2e8f0",
                  color: done || current ? "white" : "#64748b",
                }}
              >
                {done ? "✓" : i + 1}
              </div>
              <div
                style={{
                  fontSize: "0.7rem",
                  color: current ? "#2563eb" : done ? "#16a34a" : "#94a3b8",
                  fontWeight: current ? 600 : 400,
                  lineHeight: 1.3,
                }}
              >
                {step.label}
              </div>
            </div>
          );
        })}
      </div>

      {active && message && (
        <p style={{ color: "#64748b", fontSize: "0.875rem", margin: "1rem 0 0" }}>
          {message}
        </p>
      )}
    </div>
  );
}

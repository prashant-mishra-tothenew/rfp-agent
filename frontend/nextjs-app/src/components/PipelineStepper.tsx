import { Spinner } from "./Spinner";

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

  if (!active) return null;

  return (
    <div
      style={{
        background: "white",
        padding: "1.25rem 1.5rem",
        borderRadius: 12,
        marginBottom: "1rem",
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
      }}
    >
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
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  margin: "0 auto 0.5rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  background: done ? "#16a34a" : current ? "#2563eb" : "#e2e8f0",
                  color: done || current ? "white" : "#64748b",
                  boxShadow: current ? "0 0 0 3px rgba(37,99,235,0.25)" : "none",
                }}
              >
                {current ? (
                  <Spinner size="sm" variant="light" />
                ) : done ? (
                  "✓"
                ) : (
                  i + 1
                )}
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

      {message && (
        <p
          style={{
            color: "#64748b",
            fontSize: "0.8rem",
            margin: "0.75rem 0 0",
            textAlign: "center",
          }}
        >
          {message}
        </p>
      )}
    </div>
  );
}

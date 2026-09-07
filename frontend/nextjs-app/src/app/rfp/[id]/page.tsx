"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import {
  downloadUrl,
  generateProposal,
  getRequirements,
  reviewResponse,
  runPipeline,
} from "@/lib/api";

interface RequirementRow {
  req_id: string;
  description: string;
  type: string;
  mandatory: number;
  response: {
    response: string;
    status: string;
    confidence: number;
    evidence: string;
    review_required: number;
    review_status: string;
  } | null;
}

const STATUS_COLORS: Record<string, string> = {
  SUPPORTED: "#16a34a",
  PARTIALLY_SUPPORTED: "#ca8a04",
  NOT_SUPPORTED: "#dc2626",
  HUMAN_VERIFICATION_REQUIRED: "#9333ea",
};

export default function RfpDetailPage() {
  const params = useParams();
  const rfpId = params.id as string;

  const [requirements, setRequirements] = useState<RequirementRow[]>([]);
  const [compliance, setCompliance] = useState<Record<string, unknown> | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<"idle" | "processing" | "done">("idle");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [proposalReady, setProposalReady] = useState(false);
  const [pipelineError, setPipelineError] = useState("");

  useEffect(() => {
    getRequirements(rfpId).then(setRequirements).catch(console.error);
  }, [rfpId]);

  async function handlePipeline() {
    setLoading(true);
    setStep("processing");
    setPipelineError("");
    try {
      const result = await runPipeline(rfpId);
      setCompliance(result.compliance as Record<string, unknown>);
      const reqs = await getRequirements(rfpId);
      setRequirements(reqs);
      setStep("done");
    } catch (err) {
      console.error(err);
      setPipelineError(
        err instanceof Error
          ? err.message
          : "Pipeline failed. This can take several minutes — ensure Ollama is running."
      );
      setStep("idle");
    } finally {
      setLoading(false);
    }
  }

  async function handleReview(
    reqId: string,
    action: "accept" | "reject" | "edit"
  ) {
    if (action === "edit") {
      await reviewResponse(rfpId, reqId, "edit", editText);
      setEditingId(null);
    } else {
      await reviewResponse(rfpId, reqId, action);
    }
    const reqs = await getRequirements(rfpId);
    setRequirements(reqs);
  }

  async function handleProposal() {
    setLoading(true);
    try {
      await generateProposal(rfpId);
      setProposalReady(true);
    } finally {
      setLoading(false);
    }
  }

  const summary = compliance?.summary as Record<string, number> | undefined;

  return (
    <div>
      <AppNav active="rfp" />

      <h2>RFP Analysis</h2>

      {summary && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
            gap: "1rem",
            margin: "1.5rem 0",
          }}
        >
          {[
            ["Requirements", summary.total],
            ["Supported", summary.supported],
            ["Partial", summary.partial],
            ["Missing", summary.missing],
            ["Coverage", `${summary.coveragePercent}%`],
          ].map(([label, value]) => (
            <div
              key={label as string}
              style={{
                background: "white",
                padding: "1rem",
                borderRadius: 8,
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{value}</div>
              <div style={{ color: "#64748b", fontSize: "0.875rem" }}>
                {label}
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: "1rem", marginBottom: "2rem" }}>
        <button
          onClick={handlePipeline}
          disabled={loading}
          style={btnStyle("#2563eb")}
        >
          {step === "processing"
            ? "Running multi-agent pipeline (may take 5–15 min)..."
            : "Generate Draft Responses"}
        </button>
        {step === "done" && (
          <button
            onClick={handleProposal}
            disabled={loading}
            style={btnStyle("#059669")}
          >
            Generate Proposal
          </button>
        )}
        {proposalReady && (
          <>
            <a href={downloadUrl(rfpId, "docx")} style={linkStyle}>
              Download DOCX
            </a>
            <a href={downloadUrl(rfpId, "pdf")} style={linkStyle}>
              Download PDF
            </a>
          </>
        )}
      </div>

      {pipelineError && (
        <p style={{ color: "#dc2626", marginBottom: "1.5rem" }}>{pipelineError}</p>
      )}

      {requirements.length === 0 && step === "idle" && !pipelineError && (
        <p style={{ color: "#64748b" }}>
          Click &quot;Generate Draft Responses&quot; to run the LangGraph
          multi-agent pipeline (Analyzer → Knowledge → Response → Compliance).
        </p>
      )}

      {requirements.map((req) => {
        const resp = req.response;
        const status = resp?.status || "PENDING";
        const evidence = resp?.evidence
          ? JSON.parse(resp.evidence)
          : [];

        return (
          <div
            key={req.req_id}
            style={{
              background: "white",
              padding: "1.25rem",
              borderRadius: 8,
              marginBottom: "1rem",
              borderLeft: `4px solid ${STATUS_COLORS[status] || "#94a3b8"}`,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>{req.req_id}</strong>
              <span
                style={{
                  fontSize: "0.75rem",
                  background: "#f1f5f9",
                  padding: "2px 8px",
                  borderRadius: 4,
                }}
              >
                {req.type} {req.mandatory ? "• Mandatory" : ""}
              </span>
            </div>
            <p style={{ margin: "0.5rem 0" }}>{req.description}</p>

            {resp && (
              <>
                <div
                  style={{
                    background: "#f8fafc",
                    padding: "0.75rem",
                    borderRadius: 6,
                    marginTop: "0.5rem",
                  }}
                >
                  {editingId === req.req_id ? (
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      style={{ width: "100%", minHeight: 80 }}
                    />
                  ) : (
                    <p style={{ margin: 0 }}>{resp.response}</p>
                  )}
                </div>

                {evidence.length > 0 && (
                  <div style={{ marginTop: "0.5rem", fontSize: "0.875rem" }}>
                    <strong>Evidence:</strong>{" "}
                    {evidence.map((e: string, i: number) => (
                      <span
                        key={i}
                        style={{
                          background: "#e0f2fe",
                          padding: "2px 6px",
                          borderRadius: 4,
                          marginRight: 4,
                        }}
                      >
                        {e}
                      </span>
                    ))}
                  </div>
                )}

                <div
                  style={{
                    marginTop: "0.75rem",
                    display: "flex",
                    gap: "0.5rem",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      color: STATUS_COLORS[status],
                      fontWeight: 600,
                      fontSize: "0.875rem",
                    }}
                  >
                    {status.replace(/_/g, " ")}
                  </span>
                  {resp.confidence > 0 && (
                    <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                      Confidence: {Math.round(resp.confidence * 100)}%
                    </span>
                  )}
                  {editingId === req.req_id ? (
                    <button
                      onClick={() => handleReview(req.req_id, "edit")}
                      style={smallBtn("#2563eb")}
                    >
                      Save
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={() => handleReview(req.req_id, "accept")}
                        style={smallBtn("#16a34a")}
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => {
                          setEditingId(req.req_id);
                          setEditText(resp.response);
                        }}
                        style={smallBtn("#ca8a04")}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleReview(req.req_id, "reject")}
                        style={smallBtn("#dc2626")}
                      >
                        Reject
                      </button>
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}

function btnStyle(bg: string): React.CSSProperties {
  return {
    background: bg,
    color: "white",
    border: "none",
    padding: "0.75rem 1.5rem",
    borderRadius: 8,
    cursor: "pointer",
    fontSize: "0.9rem",
  };
}

function smallBtn(bg: string): React.CSSProperties {
  return {
    background: bg,
    color: "white",
    border: "none",
    padding: "4px 10px",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: "0.75rem",
  };
}

const linkStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "0.75rem 1.5rem",
  background: "#f1f5f9",
  borderRadius: 8,
  textDecoration: "none",
  color: "#0f172a",
  fontSize: "0.9rem",
};

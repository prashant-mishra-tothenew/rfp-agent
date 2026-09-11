"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { PipelineLoader } from "@/components/PipelineLoader";
import { PipelineStepper } from "@/components/PipelineStepper";
import { ProposalLoader } from "@/components/ProposalLoader";
import { Spinner } from "@/components/Spinner";
import {
  downloadUrl,
  getPipelineStatus,
  getRequirements,
  getRfp,
  PipelineStatus,
  pollPipelineUntilDone,
  ProposalStatus,
  reviewResponse,
  waitForPipeline,
  waitForProposal,
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

const REVIEW_COLORS: Record<string, string> = {
  accepted: "#16a34a",
  rejected: "#dc2626",
  edited: "#ca8a04",
  pending: "#94a3b8",
};

export default function RfpDetailPage() {
  const params = useParams();
  const rfpId = params.id as string;
  const startedRef = useRef(false);

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
  const [reviewError, setReviewError] = useState("");
  const [pipelineProgress, setPipelineProgress] = useState<PipelineStatus | null>(
    null
  );
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [proposalLoading, setProposalLoading] = useState(false);
  const [proposalProgress, setProposalProgress] = useState<ProposalStatus | null>(
    null
  );
  const [proposalElapsed, setProposalElapsed] = useState(0);

  const loadData = useCallback(async () => {
    const [rfpData, reqs] = await Promise.all([
      getRfp(rfpId),
      getRequirements(rfpId),
    ]);

    setRequirements(reqs);

    if (rfpData.rfp?.metadata) {
      try {
        const meta = JSON.parse(rfpData.rfp.metadata as string);
        if (meta.compliance) setCompliance(meta.compliance);
      } catch {
        // ignore invalid metadata
      }
    }

    if (rfpData.rfp?.status === "proposal_generated") {
      setProposalReady(true);
    }

    if (reqs.length > 0) {
      setStep("done");
      return "done";
    }

    if (rfpData.rfp?.status === "processing") {
      return "processing";
    }

    if (rfpData.rfp?.status === "completed") {
      setStep("done");
      return "done";
    }

    return "idle";
  }, [rfpId]);

  const runPipeline = useCallback(
    async (resumeOnly = false) => {
      setLoading(true);
      setStep("processing");
      setPipelineError("");
      setPipelineProgress({
        status: "running",
        progress: {
          status: "running",
          step: "starting",
          percent: 0,
          message: "Starting multi-agent pipeline…",
        },
      });

      try {
        let result: PipelineStatus;
        if (resumeOnly) {
          result = await pollPipelineUntilDone(rfpId, setPipelineProgress);
        } else {
          result = await waitForPipeline(rfpId, setPipelineProgress);
        }

        if (result.compliance) {
          setCompliance(result.compliance);
        }

        const reqs = await getRequirements(rfpId);
        setRequirements(reqs);
        setStep("done");
      } catch (err) {
        console.error(err);
        setPipelineError(
          err instanceof Error
            ? err.message
            : "Pipeline failed. Ensure Ollama and Milvus are running."
        );
        setStep("idle");
      } finally {
        setLoading(false);
        setPipelineProgress(null);
      }
    },
    [rfpId]
  );

  useEffect(() => {
    if (step !== "processing") {
      setElapsedSeconds(0);
      return;
    }
    const start = Date.now();
    const timer = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [step]);

  useEffect(() => {
    if (!proposalLoading) {
      setProposalElapsed(0);
      return;
    }
    const start = Date.now();
    const timer = setInterval(() => {
      setProposalElapsed(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [proposalLoading]);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    loadData().then(async (state) => {
      if (state === "processing") {
        await runPipeline(true);
        return;
      }

      const jobStatus = await getPipelineStatus(rfpId).catch(() => null);
      if (jobStatus?.status === "running") {
        await runPipeline(true);
        return;
      }

      if (state === "idle") {
        await runPipeline(false);
      }
    });
  }, [loadData, runPipeline, rfpId]);

  async function handleRetry() {
    startedRef.current = true;
    await runPipeline(false);
  }

  async function handleReview(
    reqId: string,
    action: "accept" | "reject" | "edit"
  ) {
    setReviewError("");
    try {
      if (action === "edit") {
        await reviewResponse(rfpId, reqId, "edit", editText);
        setEditingId(null);
      } else {
        await reviewResponse(rfpId, reqId, action);
      }
      const reqs = await getRequirements(rfpId);
      setRequirements(reqs);
    } catch (err) {
      setReviewError(
        err instanceof Error ? err.message : "Review action failed"
      );
    }
  }

  async function handleProposal() {
    setProposalLoading(true);
    setPipelineError("");
    setProposalProgress({
      status: "running",
      progress: {
        status: "running",
        step: "writing",
        percent: 0,
        message: "Starting proposal generation…",
      },
    });

    try {
      await waitForProposal(rfpId, setProposalProgress);
      setProposalReady(true);
    } catch (err) {
      setPipelineError(
        err instanceof Error ? err.message : "Proposal generation failed"
      );
    } finally {
      setProposalLoading(false);
      setProposalProgress(null);
    }
  }

  function parseEvidence(raw: string | undefined): string[] {
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  const summary = compliance?.summary as Record<string, number> | undefined;
  const progress = pipelineProgress?.progress;
  const isProcessing = step === "processing";

  return (
    <div>
      <AppNav active="generate" />

      <h2>RFP Analysis</h2>

      {isProcessing && (
        <>
          <PipelineLoader
            step={progress?.step}
            percent={progress?.percent}
            message={progress?.message}
            elapsedSeconds={elapsedSeconds}
            requirementDone={progress?.requirementDone}
            requirementTotal={progress?.requirementTotal}
          />
          <PipelineStepper
            active={isProcessing}
            currentStep={progress?.step}
            percent={progress?.percent}
            message={progress?.message}
          />
        </>
      )}

      {summary && step === "done" && (
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

      {proposalLoading && proposalProgress && (
        <ProposalLoader
          step={proposalProgress.progress?.step}
          percent={proposalProgress.progress?.percent}
          message={proposalProgress.progress?.message}
          elapsedSeconds={proposalElapsed}
          sectionDone={proposalProgress.progress?.sectionDone}
          sectionTotal={proposalProgress.progress?.sectionTotal}
        />
      )}

      <div style={{ display: "flex", gap: "1rem", marginBottom: "2rem" }}>
        {step === "done" && !proposalLoading && (
          <button
            onClick={handleProposal}
            disabled={proposalLoading || isProcessing}
            style={btnStyle("#059669", proposalLoading)}
          >
            Generate Proposal
          </button>
        )}
        {(step === "idle" || pipelineError) && !isProcessing && (
          <button
            onClick={handleRetry}
            disabled={loading}
            style={btnStyle("#2563eb", loading)}
          >
            {loading ? (
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Spinner size="sm" />
                Starting…
              </span>
            ) : pipelineError ? (
              "Retry Analysis"
            ) : (
              "Run Analysis"
            )}
          </button>
        )}
        {proposalReady && (
          <>
            <a href={downloadUrl(rfpId, "docx")} style={linkStyle}>
              Download DOCX
            </a>
            <a href={downloadUrl(rfpId, "pptx")} style={linkStyle}>
              Download PPTX
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

      {reviewError && (
        <p style={{ color: "#dc2626", marginBottom: "1.5rem" }}>{reviewError}</p>
      )}

      <div style={{ opacity: isProcessing ? 0.45 : 1, pointerEvents: isProcessing ? "none" : "auto" }}>
      {requirements.map((req) => {
        const resp = req.response;
        const status = resp?.status || "PENDING";
        const evidence = parseEvidence(resp?.evidence);
        const reviewStatus = resp?.review_status || "pending";

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
                    flexWrap: "wrap",
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
                  {reviewStatus !== "pending" && (
                    <span
                      style={{
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        color: REVIEW_COLORS[reviewStatus] || "#64748b",
                        background: "#f8fafc",
                        padding: "2px 8px",
                        borderRadius: 4,
                      }}
                    >
                      Review: {reviewStatus}
                    </span>
                  )}
                  {resp.confidence > 0 && (
                    <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                      Confidence: {Math.round(resp.confidence * 100)}%
                    </span>
                  )}
                  {editingId === req.req_id ? (
                    <button
                      type="button"
                      onClick={() => handleReview(req.req_id, "edit")}
                      style={smallBtn("#2563eb")}
                    >
                      Save
                    </button>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => handleReview(req.req_id, "accept")}
                        disabled={reviewStatus === "accepted"}
                        style={smallBtn(
                          reviewStatus === "accepted" ? "#94a3b8" : "#16a34a"
                        )}
                      >
                        {reviewStatus === "accepted" ? "Accepted" : "Accept"}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setEditingId(req.req_id);
                          setEditText(resp.response);
                        }}
                        style={smallBtn("#ca8a04")}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleReview(req.req_id, "reject")}
                        disabled={reviewStatus === "rejected"}
                        style={smallBtn(
                          reviewStatus === "rejected" ? "#94a3b8" : "#dc2626"
                        )}
                      >
                        {reviewStatus === "rejected" ? "Rejected" : "Reject"}
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
    </div>
  );
}

function btnStyle(bg: string, disabled = false): React.CSSProperties {
  return {
    background: bg,
    color: "white",
    border: "none",
    padding: "0.75rem 1.5rem",
    borderRadius: 8,
    cursor: disabled ? "not-allowed" : "pointer",
    fontSize: "0.9rem",
    opacity: disabled ? 0.8 : 1,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
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

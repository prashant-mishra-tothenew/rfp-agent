"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRfpActor } from "@/components/RfpActorProvider";
import { listRfps, RfpListItem } from "@/lib/api";
import {
  formatDateTimeInZone,
  formatTimeZoneAbbrev,
  getClientTimeZone,
} from "@/lib/datetime";
import { Spinner } from "@/components/Spinner";

const cardStyle: React.CSSProperties = {
  background: "white",
  padding: "1.25rem 1.5rem",
  borderRadius: 12,
  boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
  marginBottom: "1.5rem",
};

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    uploaded: "Uploaded",
    processing: "Processing",
    completed: "Ready for review",
    proposal_generated: "Proposal generated",
    error: "Error",
    analyzing: "Analyzing",
    analyzed: "Analyzed",
  };
  return map[status] || status;
}

export function RfpReviewQueue() {
  const { role, revision } = useRfpActor();
  const [items, setItems] = useState<RfpListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [timeZone, setTimeZone] = useState("UTC");

  useEffect(() => {
    setTimeZone(getClientTimeZone());
  }, []);

  const load = useCallback(async () => {
    setError("");
    try {
      const data = await listRfps();
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load RFP list");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    void load();
  }, [load, revision]);

  if (loading) {
    return (
      <div style={cardStyle}>
        <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Spinner size="sm" />
          Loading RFPs for review…
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={cardStyle}>
        <p style={{ color: "#dc2626", margin: 0 }}>{error}</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div style={cardStyle}>
        <h3 style={{ margin: "0 0 0.5rem" }}>RFP review queue</h3>
        <p style={{ margin: 0, color: "#64748b", fontSize: "0.9rem" }}>
          {role === "sme"
            ? "No RFPs in the system yet."
            : "You have no RFPs yet. Upload one below to start analysis."}
        </p>
      </div>
    );
  }

  const needsAttention = items.filter((item) => item.needsReview);

  return (
    <div style={cardStyle}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "1rem",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <div>
          <h3 style={{ margin: 0 }}>RFP review queue</h3>
          <p style={{ margin: "0.25rem 0 0", color: "#64748b", fontSize: "0.875rem" }}>
            {role === "sme"
              ? "All RFPs. You approve or reject each AI-generated response."
              : "Your uploads. Edit drafts here, then reviewers approve responses."}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setLoading(true);
            void load();
          }}
          style={{
            border: "1px solid #e2e8f0",
            background: "#f8fafc",
            borderRadius: 6,
            padding: "0.35rem 0.75rem",
            cursor: "pointer",
            fontSize: "0.875rem",
          }}
        >
          Refresh
        </button>
      </div>

      {needsAttention.length > 0 && role === "sme" && (
        <p style={{ margin: "0 0 1rem", fontSize: "0.875rem", color: "#b45309" }}>
          {needsAttention.length} RFP{needsAttention.length === 1 ? "" : "s"} waiting for
          your review (pending or rejected responses).
        </p>
      )}
      {needsAttention.length > 0 && role === "user" && (
        <p style={{ margin: "0 0 1rem", fontSize: "0.875rem", color: "#64748b" }}>
          {needsAttention.length} published RFP
          {needsAttention.length === 1 ? "" : "s"} awaiting reviewer approval. Unpublished
          drafts stay private until you publish.
        </p>
      )}

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #e2e8f0", textAlign: "left" }}>
              <th style={{ padding: "0.5rem" }}>Customer / file</th>
              <th style={{ padding: "0.5rem" }}>
                <div>Date</div>
                <div
                  style={{
                    fontSize: "0.65rem",
                    fontWeight: 500,
                    color: "#94a3b8",
                    marginTop: 2,
                  }}
                  title={timeZone}
                >
                  {timeZone === "UTC"
                    ? "…"
                    : formatTimeZoneAbbrev(timeZone)}
                </div>
              </th>
              <th style={{ padding: "0.5rem" }}>Status</th>
              <th style={{ padding: "0.5rem" }}>Review progress</th>
              <th style={{ padding: "0.5rem" }}>Coverage</th>
              <th style={{ padding: "0.5rem" }} />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const { review } = item;
              const reviewed = review.accepted + review.edited + review.rejected;
              const progress =
                review.total > 0
                  ? `${reviewed}/${review.total} reviewed`
                  : "—";
              return (
                <tr key={item.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "0.65rem 0.5rem" }}>
                    <div style={{ fontWeight: 600 }}>
                      {item.customer || "Contributor"}
                    </div>
                    <div style={{ color: "#64748b", fontSize: "0.8rem" }}>
                      {item.filename}
                    </div>
                  </td>
                  <td
                    style={{
                      padding: "0.65rem 0.5rem",
                      whiteSpace: "nowrap",
                      color: "#475569",
                      fontSize: "0.8rem",
                    }}
                  >
                    {formatDateTimeInZone(
                      item.updatedAt || item.createdAt,
                      timeZone
                    )}
                  </td>
                  <td style={{ padding: "0.65rem 0.5rem" }}>
                    {statusLabel(item.status)}
                    {role === "user" && item.submissionStatus === "draft" && (
                      <span
                        style={{
                          marginLeft: 6,
                          fontSize: "0.75rem",
                          color: "#2563eb",
                          fontWeight: 600,
                        }}
                      >
                        Draft
                      </span>
                    )}
                    {role === "user" &&
                      item.submissionStatus === "published" &&
                      !item.needsReview && (
                        <span
                          style={{
                            marginLeft: 6,
                            fontSize: "0.75rem",
                            color: "#047857",
                            fontWeight: 600,
                          }}
                        >
                          Published
                        </span>
                      )}
                    {item.needsReview && role === "sme" && (
                      <span
                        style={{
                          marginLeft: 6,
                          fontSize: "0.75rem",
                          color: "#b45309",
                          fontWeight: 600,
                        }}
                      >
                        Needs your review
                      </span>
                    )}
                    {item.needsReview && role === "user" && (
                      <span
                        style={{
                          marginLeft: 6,
                          fontSize: "0.75rem",
                          color: "#64748b",
                          fontWeight: 600,
                        }}
                      >
                        Awaiting reviewer
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "0.65rem 0.5rem" }}>
                    {progress}
                    {review.total > 0 && (
                      <div style={{ color: "#64748b", fontSize: "0.75rem" }}>
                        {review.pending} pending · {review.rejected} rejected
                      </div>
                    )}
                  </td>
                  <td style={{ padding: "0.65rem 0.5rem" }}>
                    {item.coveragePercent != null ? `${item.coveragePercent}%` : "—"}
                  </td>
                  <td style={{ padding: "0.65rem 0.5rem", textAlign: "right" }}>
                    <Link
                      href={`/rfp/${item.id}`}
                      style={{
                        color: "#2563eb",
                        fontWeight: 600,
                        textDecoration: "none",
                      }}
                    >
                      Open
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

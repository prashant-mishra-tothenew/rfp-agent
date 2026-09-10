"use client";

import { useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import {
  ingestKnowledge,
  KnowledgeDocument,
  listKnowledgeDocuments,
} from "@/lib/api";
import {
  APPROVAL_STATUSES,
  DOCUMENT_TYPES,
  INDUSTRIES,
} from "@/lib/constants";

const inputStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  marginTop: "0.25rem",
  padding: "0.5rem",
  border: "1px solid #e2e8f0",
  borderRadius: 6,
};

const cardStyle: React.CSSProperties = {
  background: "white",
  padding: "2rem",
  borderRadius: 12,
  boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
};

export default function KnowledgePage() {
  const [files, setFiles] = useState<FileList | null>(null);
  const [documentId, setDocumentId] = useState("");
  const [documentType, setDocumentType] = useState("historical");
  const [industry, setIndustry] = useState("Technology");
  const [year, setYear] = useState(new Date().getFullYear());
  const [approvalStatus, setApprovalStatus] = useState("approved");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);

  async function loadDocuments() {
    try {
      const docs = await listKnowledgeDocuments();
      setDocuments(docs);
    } catch {
      setDocuments([]);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!files || files.length === 0) {
      setError("Please select at least one PDF or DOCX file");
      return;
    }

    setLoading(true);
    setError("");

    try {
      for (const file of Array.from(files)) {
        await ingestKnowledge(file, {
          documentId: documentId || undefined,
          documentType,
          industry,
          year,
          approvalStatus,
        });
      }

      setFiles(null);
      setDocumentId("");
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingestion failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <AppNav active="knowledge" />

      <h2 style={{ marginBottom: "0.5rem", marginTop: "1.5rem" }}>
        Knowledge Base
      </h2>
      <p style={{ color: "#64748b", marginBottom: "2rem" }}>
        Upload historical RFPs, proposal responses, case studies, and company
        documents. Content is chunked, embedded, and stored in Milvus for
        evidence-backed retrieval.
      </p>

      <form onSubmit={handleSubmit} style={{ ...cardStyle, marginBottom: "2rem" }}>
        <div
          style={{
            border: "2px dashed #cbd5e1",
            borderRadius: 8,
            padding: "2rem",
            textAlign: "center",
            marginBottom: "1.5rem",
          }}
        >
          <input
            type="file"
            accept=".pdf,.docx"
            multiple
            onChange={(e) => setFiles(e.target.files)}
            style={{ marginBottom: "0.5rem" }}
          />
          <p style={{ color: "#94a3b8", fontSize: "0.875rem", margin: 0 }}>
            PDF or DOCX — select one or more files
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "1rem",
            marginBottom: "1.5rem",
          }}
        >
          <label>
            Document ID (optional)
            <input
              type="text"
              value={documentId}
              onChange={(e) => setDocumentId(e.target.value)}
              placeholder="e.g. RFP-2025-017"
              style={inputStyle}
            />
          </label>

          <label>
            Document Type
            <select
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              style={inputStyle}
            >
              {DOCUMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Industry
            <select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              style={inputStyle}
            >
              {INDUSTRIES.map((i) => (
                <option key={i} value={i}>
                  {i}
                </option>
              ))}
            </select>
          </label>

          <label>
            Year
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(parseInt(e.target.value, 10))}
              min={2000}
              max={2100}
              style={inputStyle}
            />
          </label>

          <label>
            Approval Status
            <select
              value={approvalStatus}
              onChange={(e) => setApprovalStatus(e.target.value)}
              style={inputStyle}
            >
              {APPROVAL_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            <span style={{ fontSize: "0.8rem", color: "#64748b" }}>
              Use <strong>Approved</strong> for past proposal responses used in
              auto-drafting. Draft and expired documents are excluded from the
              pipeline.
            </span>
          </label>
        </div>

        {error && (
          <p style={{ color: "#dc2626", marginBottom: "1rem" }}>{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            background: "#059669",
            color: "white",
            border: "none",
            padding: "0.75rem 2rem",
            borderRadius: 8,
            fontSize: "1rem",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Ingesting into Milvus..." : "Ingest Documents"}
        </button>
      </form>

      <div style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>Ingested Documents</h3>
        {documents.length === 0 ? (
          <p style={{ color: "#64748b" }}>
            No documents ingested yet. Upload historical content above to enable
            RAG retrieval.
          </p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #e2e8f0" }}>
                <th style={{ padding: "0.5rem 0" }}>Filename</th>
                <th>Type</th>
                <th>Industry</th>
                <th>Year</th>
                <th>Status</th>
                <th>Chunks</th>
                <th>Ingested</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr
                  key={doc.id}
                  style={{ borderBottom: "1px solid #f1f5f9" }}
                >
                  <td style={{ padding: "0.75rem 0" }}>
                    <div style={{ fontWeight: 500 }}>{doc.filename}</div>
                    <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                      {doc.document_id}
                    </div>
                  </td>
                  <td>{doc.document_type}</td>
                  <td>{doc.industry || "—"}</td>
                  <td>{doc.year}</td>
                  <td>
                    <span
                      style={{
                        background:
                          doc.approval_status === "approved"
                            ? "#dcfce7"
                            : "#fef3c7",
                        color:
                          doc.approval_status === "approved"
                            ? "#166534"
                            : "#92400e",
                        padding: "2px 8px",
                        borderRadius: 4,
                        fontSize: "0.75rem",
                      }}
                    >
                      {doc.approval_status}
                    </span>
                  </td>
                  <td>{doc.chunks_ingested}</td>
                  <td style={{ fontSize: "0.875rem", color: "#64748b" }}>
                    {new Date(doc.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

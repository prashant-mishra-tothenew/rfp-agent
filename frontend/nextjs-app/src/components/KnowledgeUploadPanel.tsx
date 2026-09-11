"use client";

import { useEffect, useState } from "react";
import { Spinner } from "@/components/Spinner";
import {
  deleteKnowledgeDocument,
  deleteKnowledgeDocuments,
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

export function KnowledgeUploadPanel() {
  const [files, setFiles] = useState<FileList | null>(null);
  const [documentId, setDocumentId] = useState("");
  const [documentType, setDocumentType] = useState("historical");
  const [industry, setIndustry] = useState("Technology");
  const [year, setYear] = useState(() => new Date().getFullYear());
  const [approvalStatus, setApprovalStatus] = useState("historical");
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);

  const allSelected =
    documents.length > 0 && selectedIds.size === documents.length;
  const someSelected = selectedIds.size > 0 && !allSelected;

  async function loadDocuments() {
    try {
      const docs = await listKnowledgeDocuments();
      setDocuments(docs);
      setSelectedIds((prev) => {
        const valid = new Set(docs.map((doc) => doc.id));
        const next = new Set<string>();
        prev.forEach((id) => {
          if (valid.has(id)) next.add(id);
        });
        return next;
      });
    } catch {
      setDocuments([]);
      setSelectedIds(new Set());
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (allSelected) {
      setSelectedIds(new Set());
      return;
    }
    setSelectedIds(new Set(documents.map((doc) => doc.id)));
  }

  async function handleBulkDelete() {
    if (selectedIds.size === 0) return;

    const confirmed = window.confirm(
      `Remove ${selectedIds.size} document(s) from the knowledge base?\n\nThis deletes Milvus vectors, SQLite records, and uploaded files.`
    );
    if (!confirmed) return;

    setBulkDeleting(true);
    setError("");
    try {
      await deleteKnowledgeDocuments(Array.from(selectedIds));
      setSelectedIds(new Set());
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk delete failed");
    } finally {
      setBulkDeleting(false);
    }
  }

  async function handleDelete(doc: KnowledgeDocument) {
    const confirmed = window.confirm(
      `Remove "${doc.filename}" from the knowledge base?\n\nThis deletes Milvus vectors, the SQLite record, and the uploaded file.`
    );
    if (!confirmed) return;

    setDeletingId(doc.id);
    setError("");
    try {
      await deleteKnowledgeDocument(doc.id);
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!files || files.length === 0) {
      setError("Please select at least one file");
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
    <div role="tabpanel" aria-label="Knowledge Base">
      <h2 style={{ marginBottom: "0.5rem" }}>Historical RFP &amp; Knowledge Upload</h2>
      <p style={{ color: "#64748b", marginBottom: "1.5rem" }}>
        Upload past proposals, case studies, and capability documents. Content is
        chunked, embedded, and stored in Milvus for evidence retrieval during new
        RFP analysis.
      </p>

      <form onSubmit={handleSubmit} style={{ ...cardStyle, marginBottom: "2rem" }}>
        <div
          style={{
            border: "2px dashed #86efac",
            borderRadius: 8,
            padding: "2rem",
            textAlign: "center",
            marginBottom: "1.5rem",
            background: "#f0fdf4",
          }}
        >
          <input
            type="file"
            accept=".pdf,.docx,.pptx"
            multiple
            onChange={(e) => setFiles(e.target.files)}
            style={{ marginBottom: "0.5rem" }}
          />
          <p style={{ color: "#64748b", fontSize: "0.875rem", margin: 0 }}>
            PDF / DOCX / PPTX — select one or more historical documents
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
              placeholder="e.g. TRAIN-RFP-001"
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
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          {loading && <Spinner size="sm" />}
          {loading ? "Ingesting into Milvus…" : "Ingest Documents"}
        </button>
      </form>

      <div style={cardStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "1rem",
            flexWrap: "wrap",
            marginBottom: "1rem",
          }}
        >
          <h3 style={{ margin: 0 }}>Ingested Documents</h3>
          {documents.length > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <span style={{ fontSize: "0.875rem", color: "#64748b" }}>
                {selectedIds.size > 0
                  ? `${selectedIds.size} selected`
                  : `${documents.length} total`}
              </span>
              <button
                type="button"
                onClick={handleBulkDelete}
                disabled={
                  selectedIds.size === 0 ||
                  bulkDeleting ||
                  deletingId !== null ||
                  loading
                }
                style={{
                  background: selectedIds.size > 0 ? "#dc2626" : "#f1f5f9",
                  color: selectedIds.size > 0 ? "#fff" : "#94a3b8",
                  border: "none",
                  padding: "0.5rem 1rem",
                  borderRadius: 8,
                  fontSize: "0.875rem",
                  cursor:
                    selectedIds.size === 0 || bulkDeleting
                      ? "not-allowed"
                      : "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                {bulkDeleting && <Spinner size="sm" />}
                Delete selected
              </button>
            </div>
          )}
        </div>
        {documents.length === 0 ? (
          <p style={{ color: "#64748b" }}>
            No documents ingested yet. Upload historical proposals above to enable
            evidence retrieval.
          </p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #e2e8f0" }}>
                <th style={{ width: 36, padding: "0.5rem 0" }}>
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(el) => {
                      if (el) el.indeterminate = someSelected;
                    }}
                    onChange={toggleSelectAll}
                    disabled={bulkDeleting || loading}
                    aria-label="Select all documents"
                  />
                </th>
                <th style={{ padding: "0.5rem 0" }}>Filename</th>
                <th>Type</th>
                <th>Industry</th>
                <th>Year</th>
                <th>Status</th>
                <th>Chunks</th>
                <th>Ingested</th>
                <th style={{ width: 90 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr
                  key={doc.id}
                  style={{
                    borderBottom: "1px solid #f1f5f9",
                    background: selectedIds.has(doc.id) ? "#f8fafc" : "transparent",
                  }}
                >
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(doc.id)}
                      onChange={() => toggleSelect(doc.id)}
                      disabled={bulkDeleting || deletingId !== null || loading}
                      aria-label={`Select ${doc.filename}`}
                    />
                  </td>
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
                  <td>
                    <button
                      type="button"
                      onClick={() => handleDelete(doc)}
                      disabled={
                        deletingId === doc.id || bulkDeleting || loading
                      }
                      style={{
                        background: "#fff",
                        color: "#dc2626",
                        border: "1px solid #fecaca",
                        padding: "4px 10px",
                        borderRadius: 6,
                        fontSize: "0.75rem",
                        cursor:
                          deletingId === doc.id || loading
                            ? "not-allowed"
                            : "pointer",
                        opacity: deletingId === doc.id ? 0.7 : 1,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.35rem",
                      }}
                    >
                      {deletingId === doc.id && <Spinner size="sm" />}
                      Remove
                    </button>
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

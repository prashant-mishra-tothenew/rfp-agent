"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@/components/Spinner";
import { uploadRfp } from "@/lib/api";
import { INDUSTRIES } from "@/lib/constants";

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

export function RfpUploadPanel() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [customer, setCustomer] = useState("");
  const [industry, setIndustry] = useState("Technology");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Please select an RFP file (PDF, DOCX, or PPTX)");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const result = await uploadRfp(file, customer, industry);
      router.push(`/rfp/${result.id}`);
    } catch {
      setError("Upload failed. Is the API running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div role="tabpanel" aria-label="Generate RFP">
      <h2 style={{ marginBottom: "0.5rem" }}>Upload New RFP</h2>
      <p style={{ color: "#64748b", marginBottom: "1.5rem" }}>
        Upload a customer RFP to extract requirements, retrieve evidence from the
        knowledge base, and generate draft responses plus a proposal deck.
      </p>

      <form onSubmit={handleSubmit} style={cardStyle}>
        <div
          style={{
            border: "2px dashed #cbd5e1",
            borderRadius: 8,
            padding: "3rem",
            textAlign: "center",
            marginBottom: "1.5rem",
            background: "#f8fafc",
          }}
        >
          <input
            type="file"
            accept=".pdf,.docx,.pptx"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            style={{ marginBottom: "0.5rem" }}
          />
          <p style={{ color: "#94a3b8", fontSize: "0.875rem", margin: 0 }}>
            PDF / DOCX / PPTX — customer RFP document
          </p>
        </div>

        <label style={{ display: "block", marginBottom: "1rem" }}>
          Customer
          <input
            type="text"
            value={customer}
            onChange={(e) => setCustomer(e.target.value)}
            placeholder="Customer name"
            style={inputStyle}
          />
        </label>

        <label style={{ display: "block", marginBottom: "1.5rem" }}>
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

        {error && (
          <p style={{ color: "#dc2626", marginBottom: "1rem" }}>{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            background: "#2563eb",
            color: "white",
            border: "none",
            padding: "0.75rem 2rem",
            borderRadius: 8,
            fontSize: "1rem",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.8 : 1,
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          {loading && <Spinner size="sm" />}
          {loading ? "Uploading & starting analysis…" : "Upload & Analyze"}
        </button>
      </form>
    </div>
  );
}

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
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [customer, setCustomer] = useState("");
  const [industry, setIndustry] = useState("Technology");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const normalizedUrl = websiteUrl.trim();
    if (!file && !normalizedUrl) {
      setError("Provide an RFP document, a website URL, or both");
      return;
    }
    if (normalizedUrl) {
      try {
        const parsed = new URL(normalizedUrl);
        if (!["http:", "https:"].includes(parsed.protocol)) throw new Error();
      } catch {
        setError("Enter a valid website URL beginning with http:// or https://");
        return;
      }
    }

    setLoading(true);
    setError("");
    try {
      const result = await uploadRfp(file, normalizedUrl, customer, industry);
      router.push(`/rfp/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div role="tabpanel" aria-label="Generate RFP">
      <h2 style={{ marginBottom: "0.5rem" }}>Analyze RFP Sources</h2>
      <p style={{ color: "#64748b", marginBottom: "1.5rem" }}>
        Upload a customer RFP, enter a website URL, or provide both. Website
        pages are crawled to identify visible features and capabilities.
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
            Optional PDF / DOCX / PPTX document
          </p>
        </div>

        <div
          style={{
            textAlign: "center",
            color: "#64748b",
            fontSize: "0.875rem",
            fontWeight: 600,
            margin: "-0.5rem 0 1rem",
          }}
        >
          AND / OR
        </div>

        <label style={{ display: "block", marginBottom: "1.5rem" }}>
          Website URL
          <input
            type="url"
            value={websiteUrl}
            onChange={(e) => setWebsiteUrl(e.target.value)}
            placeholder="https://example.com"
            style={inputStyle}
          />
          <span
            style={{
              display: "block",
              color: "#64748b",
              fontSize: "0.75rem",
              marginTop: "0.35rem",
            }}
          >
            Up to 25 public pages on the same website will be analyzed.
          </span>
        </label>

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
          {loading ? "Starting analysis…" : "Upload & Analyze"}
        </button>
      </form>
    </div>
  );
}

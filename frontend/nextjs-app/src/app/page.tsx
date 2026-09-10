"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { uploadRfp } from "@/lib/api";
import { INDUSTRIES } from "@/lib/constants";

export default function HomePage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [customer, setCustomer] = useState("");
  const [industry, setIndustry] = useState("Technology");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Please select an RFP file (PDF or DOCX)");
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
    <div>
      <AppNav active="rfp" />

      <h2 style={{ marginBottom: "0.5rem", marginTop: "1.5rem" }}>Upload New RFP</h2>
      <p style={{ color: "#64748b", marginBottom: "2rem" }}>
        Upload a PDF or DOCX RFP to analyze requirements and generate evidence-backed responses.
      </p>

      <form
        onSubmit={handleSubmit}
        style={{
          background: "white",
          padding: "2rem",
          borderRadius: 12,
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        }}
      >
        <div
          style={{
            border: "2px dashed #cbd5e1",
            borderRadius: 8,
            padding: "3rem",
            textAlign: "center",
            marginBottom: "1.5rem",
          }}
        >
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            style={{ marginBottom: "0.5rem" }}
          />
          <p style={{ color: "#94a3b8", fontSize: "0.875rem", margin: 0 }}>
            Drag &amp; drop RFP PDF / DOCX
          </p>
        </div>

        <label style={{ display: "block", marginBottom: "1rem" }}>
          Customer
          <input
            type="text"
            value={customer}
            onChange={(e) => setCustomer(e.target.value)}
            placeholder="Customer name"
            style={{
              display: "block",
              width: "100%",
              marginTop: "0.25rem",
              padding: "0.5rem",
              border: "1px solid #e2e8f0",
              borderRadius: 6,
            }}
          />
        </label>

        <label style={{ display: "block", marginBottom: "1.5rem" }}>
          Industry
          <select
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            style={{
              display: "block",
              width: "100%",
              marginTop: "0.25rem",
              padding: "0.5rem",
              border: "1px solid #e2e8f0",
              borderRadius: 6,
            }}
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
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Uploading..." : "Upload & Analyze"}
        </button>
      </form>
    </div>
  );
}

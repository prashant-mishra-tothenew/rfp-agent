const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001";

export async function uploadRfp(
  file: File,
  customer: string,
  industry: string
) {
  const form = new FormData();
  form.append("file", file);
  form.append("customer", customer);
  form.append("industry", industry);

  const res = await fetch(`${API_URL}/api/rfps`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function runPipeline(rfpId: string) {
  const res = await fetch(`${API_URL}/api/rfps/${rfpId}/pipeline`, {
    method: "POST",
    signal: AbortSignal.timeout(20 * 60 * 1000),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || body.message || `Pipeline failed (${res.status})`);
  }
  return res.json();
}

export async function getRfp(rfpId: string) {
  const res = await fetch(`${API_URL}/api/rfps/${rfpId}`);
  if (!res.ok) throw new Error("Failed to fetch RFP");
  return res.json();
}

export async function getRequirements(rfpId: string) {
  const res = await fetch(`${API_URL}/api/rfps/${rfpId}/requirements`);
  if (!res.ok) throw new Error("Failed to fetch requirements");
  return res.json();
}

export async function reviewResponse(
  rfpId: string,
  requirementId: string,
  action: "accept" | "reject" | "edit",
  response?: string
) {
  const res = await fetch(`${API_URL}/api/rfps/${rfpId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ requirementId, action, response }),
  });
  if (!res.ok) throw new Error("Review failed");
  return res.json();
}

export async function generateProposal(rfpId: string) {
  const res = await fetch(`${API_URL}/api/rfps/${rfpId}/proposal`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Proposal generation failed");
  return res.json();
}

export function downloadUrl(rfpId: string, format: "docx" | "pdf") {
  return `${API_URL}/api/rfps/${rfpId}/download/${format}`;
}

export interface KnowledgeDocument {
  id: string;
  document_id: string;
  filename: string;
  document_type: string;
  industry: string;
  year: number;
  approval_status: string;
  chunks_ingested: number;
  created_at: string;
}

export interface IngestKnowledgeResult {
  ingested: number;
  document_id: string;
  filename: string;
  document_type: string;
  industry: string;
  year: number;
  approval_status: string;
}

export async function ingestKnowledge(
  file: File,
  options: {
    documentId?: string;
    documentType: string;
    industry: string;
    year: number;
    approvalStatus: string;
  }
): Promise<IngestKnowledgeResult> {
  const form = new FormData();
  form.append("file", file);
  if (options.documentId) form.append("document_id", options.documentId);
  form.append("document_type", options.documentType);
  form.append("industry", options.industry);
  form.append("year", String(options.year));
  form.append("approval_status", options.approvalStatus);

  const res = await fetch(`${API_URL}/api/knowledge/ingest`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || "Knowledge ingestion failed");
  }

  return res.json();
}

export async function listKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  const res = await fetch(`${API_URL}/api/knowledge`);
  if (!res.ok) throw new Error("Failed to load knowledge documents");
  const data = await res.json();
  return data.documents;
}

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
  if (!res.ok) {
    if (res.status === 413) {
      throw new Error("File is too large. Maximum upload size is 50 MB per file.");
    }
    throw new Error("Upload failed");
  }
  return res.json();
}

export interface PipelineProgress {
  status: string;
  step?: string;
  message?: string;
  percent?: number;
  requirementTotal?: number;
  requirementDone?: number;
}

export interface PipelineStatus {
  status: "idle" | "running" | "completed" | "error";
  error?: string;
  compliance?: Record<string, unknown>;
  progress?: PipelineProgress;
}

export async function startPipeline(rfpId: string) {
  const res = await fetch(`${API_URL}/api/rfps/${rfpId}/pipeline`, {
    method: "POST",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || body.message || `Pipeline failed (${res.status})`);
  }
  return res.json();
}

export async function getPipelineStatus(rfpId: string): Promise<PipelineStatus> {
  const res = await fetch(`${API_URL}/api/rfps/${rfpId}/pipeline/status`);
  if (!res.ok) throw new Error("Failed to fetch pipeline status");
  return res.json();
}

export async function pollPipelineUntilDone(
  rfpId: string,
  onProgress?: (status: PipelineStatus) => void
): Promise<PipelineStatus> {
  for (let i = 0; i < 600; i++) {
    const status = await getPipelineStatus(rfpId);
    onProgress?.(status);

    if (status.status === "completed") return status;
    if (status.status === "error") {
      throw new Error(status.error || "Pipeline failed");
    }

    await new Promise((r) => setTimeout(r, 2000));
  }

  throw new Error("Pipeline timed out after 20 minutes");
}

export async function waitForPipeline(
  rfpId: string,
  onProgress?: (status: PipelineStatus) => void
): Promise<PipelineStatus> {
  const current = await getPipelineStatus(rfpId);
  if (current.status !== "running") {
    await startPipeline(rfpId);
  }
  return pollPipelineUntilDone(rfpId, onProgress);
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

export interface ProposalProgress {
  status: string;
  step?: string;
  message?: string;
  percent?: number;
  sectionDone?: number;
  sectionTotal?: number;
}

export interface ProposalStatus {
  status: "idle" | "running" | "completed" | "error";
  error?: string;
  docxPath?: string;
  pptxPath?: string;
  pdfPath?: string | null;
  progress?: ProposalProgress;
}

export async function startProposal(rfpId: string) {
  const res = await fetch(`${API_URL}/api/rfps/${rfpId}/proposal`, {
    method: "POST",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || "Proposal generation failed");
  }
  return res.json();
}

export async function getProposalStatus(rfpId: string): Promise<ProposalStatus> {
  const res = await fetch(`${API_URL}/api/rfps/${rfpId}/proposal/status`);
  if (!res.ok) throw new Error("Failed to fetch proposal status");
  return res.json();
}

export async function pollProposalUntilDone(
  rfpId: string,
  onProgress?: (status: ProposalStatus) => void
): Promise<ProposalStatus> {
  for (let i = 0; i < 450; i++) {
    const status = await getProposalStatus(rfpId);
    onProgress?.(status);

    if (status.status === "completed") return status;
    if (status.status === "error") {
      throw new Error(status.error || "Proposal generation failed");
    }

    await new Promise((r) => setTimeout(r, 1500));
  }

  throw new Error("Proposal generation timed out after 11 minutes");
}

export async function waitForProposal(
  rfpId: string,
  onProgress?: (status: ProposalStatus) => void
): Promise<ProposalStatus> {
  const current = await getProposalStatus(rfpId);
  if (current.status !== "running") {
    await startProposal(rfpId);
  }
  return pollProposalUntilDone(rfpId, onProgress);
}

export function downloadUrl(rfpId: string, format: "docx" | "pptx" | "pdf") {
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
    if (res.status === 413) {
      throw new Error(
        "File is too large. Maximum upload size is 50 MB per file."
      );
    }
    throw new Error(
      (body as { error?: string }).error || "Knowledge ingestion failed"
    );
  }

  return res.json();
}

export async function listKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  const res = await fetch(`${API_URL}/api/knowledge`);
  if (!res.ok) throw new Error("Failed to load knowledge documents");
  const data = await res.json();
  return data.documents;
}

export async function deleteKnowledgeDocument(id: string) {
  const res = await fetch(`${API_URL}/api/knowledge/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || "Failed to delete document");
  }
  return res.json();
}

export async function deleteKnowledgeDocuments(ids: string[]) {
  const res = await fetch(`${API_URL}/api/knowledge/bulk-delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || "Failed to delete documents");
  }
  return res.json() as Promise<{
    deleted_count: number;
    not_found: string[];
  }>;
}

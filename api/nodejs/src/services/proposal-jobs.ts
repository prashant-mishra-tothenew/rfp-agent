export interface ProposalJobState {
  status: "idle" | "running" | "completed" | "error";
  error?: string;
  docxPath?: string;
  pptxPath?: string;
  pdfPath?: string | null;
}

const jobs = new Map<string, ProposalJobState>();

export function getProposalJob(rfpId: string): ProposalJobState {
  return jobs.get(rfpId) ?? { status: "idle" };
}

export function setProposalJob(rfpId: string, state: ProposalJobState): void {
  jobs.set(rfpId, state);
}

export function clearProposalJob(rfpId: string): void {
  jobs.delete(rfpId);
}

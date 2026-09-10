export interface PipelineJobState {
  status: "idle" | "running" | "completed" | "error";
  error?: string;
  compliance?: Record<string, unknown>;
}

const jobs = new Map<string, PipelineJobState>();

export function getPipelineJob(rfpId: string): PipelineJobState {
  return jobs.get(rfpId) ?? { status: "idle" };
}

export function setPipelineJob(rfpId: string, state: PipelineJobState): void {
  jobs.set(rfpId, state);
}

export function clearPipelineJob(rfpId: string): void {
  jobs.delete(rfpId);
}

import http from "node:http";
import https from "node:https";

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 5 * 60 * 1000;
const PIPELINE_TIMEOUT_MS = 20 * 60 * 1000;
const PROPOSAL_TIMEOUT_MS = 15 * 60 * 1000;

function postJson<T>(
  endpoint: string,
  body: unknown,
  timeoutMs: number
): Promise<T> {
  return new Promise((resolve, reject) => {
    const url = new URL(`${AI_SERVICE_URL}${endpoint}`);
    const data = JSON.stringify(body);
    const transport = url.protocol === "https:" ? https : http;

    const req = transport.request(
      {
        hostname: url.hostname,
        port: url.port,
        path: `${url.pathname}${url.search}`,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(data),
        },
        timeout: timeoutMs,
      },
      (res) => {
        let text = "";
        res.on("data", (chunk) => {
          text += chunk;
        });
        res.on("end", () => {
          if ((res.statusCode ?? 500) >= 400) {
            let message = text;
            try {
              const parsed = JSON.parse(text) as {
                detail?: string | Array<{ msg?: string }>;
                error?: string;
              };
              if (typeof parsed.detail === "string") {
                message = parsed.detail;
              } else if (Array.isArray(parsed.detail)) {
                message = parsed.detail
                  .map((item) => item.msg)
                  .filter(Boolean)
                  .join("; ");
              } else if (parsed.error) {
                message = parsed.error;
              }
            } catch {
              // keep raw text
            }
            reject(
              new Error(`AI service error (${res.statusCode}): ${message}`)
            );
            return;
          }
          try {
            resolve(JSON.parse(text) as T);
          } catch {
            reject(new Error(`Invalid JSON from AI service: ${text.slice(0, 200)}`));
          }
        });
      }
    );

    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error(`AI service request timed out after ${timeoutMs}ms`));
    });
    req.write(data);
    req.end();
  });
}

export async function aiRequest<T>(
  endpoint: string,
  options: { method?: string; body?: string } = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<T> {
  if (options.method && options.method !== "POST") {
    throw new Error("Only POST is supported by aiRequest");
  }
  const body = options.body ? JSON.parse(options.body) : {};
  return postJson<T>(endpoint, body, timeoutMs);
}

export async function analyzeRfp(filePath: string) {
  return aiRequest<{
    metadata: Record<string, unknown>;
    requirements: Array<Record<string, unknown>>;
  }>(
    "/ai/rfp/analyze",
    { body: JSON.stringify({ file_path: filePath }) },
    10 * 60 * 1000
  );
}

export interface PipelineProgress {
  status: string;
  step?: string;
  message?: string;
  percent?: number;
  requirementTotal?: number;
  requirementDone?: number;
}

function getJson<T>(endpoint: string, timeoutMs: number = 10_000): Promise<T> {
  return new Promise((resolve, reject) => {
    const url = new URL(`${AI_SERVICE_URL}${endpoint}`);
    const transport = url.protocol === "https:" ? https : http;

    const req = transport.request(
      {
        hostname: url.hostname,
        port: url.port,
        path: `${url.pathname}${url.search}`,
        method: "GET",
        timeout: timeoutMs,
      },
      (res) => {
        let text = "";
        res.on("data", (chunk) => {
          text += chunk;
        });
        res.on("end", () => {
          if ((res.statusCode ?? 500) >= 400) {
            reject(new Error(`AI service error (${res.statusCode}): ${text}`));
            return;
          }
          try {
            resolve(JSON.parse(text) as T);
          } catch {
            reject(new Error(`Invalid JSON from AI service: ${text.slice(0, 200)}`));
          }
        });
      }
    );

    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error(`AI service request timed out after ${timeoutMs}ms`));
    });
    req.end();
  });
}

export async function getPipelineProgress(jobId: string): Promise<PipelineProgress> {
  return getJson<PipelineProgress>(`/ai/rfp/pipeline/progress/${jobId}`);
}

export async function getProposalProgress(jobId: string): Promise<PipelineProgress> {
  return getJson<PipelineProgress>(`/ai/proposal/progress/${jobId}`);
}

export async function runPipeline(
  filePath: string,
  filters?: Record<string, unknown>,
  jobId?: string
) {
  return aiRequest<{
    metadata: Record<string, unknown>;
    requirements: Array<Record<string, unknown>>;
    responses: Array<Record<string, unknown>>;
    compliance: Record<string, unknown>;
  }>(
    "/ai/rfp/pipeline",
    {
      body: JSON.stringify({ file_path: filePath, filters, job_id: jobId }),
    },
    PIPELINE_TIMEOUT_MS
  );
}

export async function convertProposalPdf(docxPath: string) {
  return aiRequest<{ pdfPath: string }>(
    "/ai/proposal/convert-pdf",
    { body: JSON.stringify({ docx_path: docxPath }) },
    60_000
  );
}

export async function generateProposal(data: {
  rfp_id: string;
  metadata: Record<string, unknown>;
  requirements: Array<Record<string, unknown>>;
  responses: Array<Record<string, unknown>>;
  compliance: Record<string, unknown>;
  job_id?: string;
}) {
  return aiRequest<{
    proposal: Record<string, unknown>;
    docxPath: string;
    pptxPath: string;
    pdfPath: string | null;
  }>("/ai/proposal/generate", { body: JSON.stringify(data) }, PROPOSAL_TIMEOUT_MS);
}

export async function ingestKnowledge(data: {
  file_path: string;
  document_id: string;
  document_type?: string;
  industry?: string;
  year?: number;
  approval_status?: string;
}) {
  return aiRequest<{ ingested: number; document_id: string }>(
    "/ai/knowledge/ingest",
    { body: JSON.stringify(data) }
  );
}

export async function deleteKnowledgeVectors(documentId: string) {
  return aiRequest<{ deleted: number; document_id: string }>(
    "/ai/knowledge/delete",
    { body: JSON.stringify({ document_id: documentId }) }
  );
}

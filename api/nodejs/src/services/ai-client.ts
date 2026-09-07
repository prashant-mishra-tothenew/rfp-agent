import http from "node:http";
import https from "node:https";

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 5 * 60 * 1000;
const PIPELINE_TIMEOUT_MS = 20 * 60 * 1000;

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

export async function runPipeline(
  filePath: string,
  filters?: Record<string, unknown>
) {
  return aiRequest<{
    metadata: Record<string, unknown>;
    requirements: Array<Record<string, unknown>>;
    responses: Array<Record<string, unknown>>;
    compliance: Record<string, unknown>;
  }>(
    "/ai/rfp/pipeline",
    { body: JSON.stringify({ file_path: filePath, filters }) },
    PIPELINE_TIMEOUT_MS
  );
}

export async function generateProposal(data: {
  rfp_id: string;
  metadata: Record<string, unknown>;
  requirements: Array<Record<string, unknown>>;
  responses: Array<Record<string, unknown>>;
  compliance: Record<string, unknown>;
}) {
  return aiRequest<{
    proposal: Record<string, unknown>;
    docxPath: string;
    pdfPath: string | null;
  }>("/ai/proposal/generate", { body: JSON.stringify(data) });
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

import { FastifyInstance } from "fastify";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { v4 as uuidv4 } from "uuid";
import { db } from "../db/index.js";
import {
  analyzeRfp,
  deleteKnowledgeVectors,
  convertProposalPdf,
  generateProposal,
  getPipelineProgress,
  getProposalProgress,
  ingestKnowledge,
  runPipeline,
} from "../services/ai-client.js";
import {
  getPipelineJob,
  setPipelineJob,
} from "../services/pipeline-jobs.js";
import {
  getProposalJob,
  setProposalJob,
} from "../services/proposal-jobs.js";

const REPO_ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../../.."
);
const UPLOAD_DIR =
  process.env.UPLOAD_DIR || path.join(REPO_ROOT, "data/uploads");
const PROPOSAL_DIR =
  process.env.PROPOSAL_DIR || path.join(REPO_ROOT, "data/proposals");
const LEGACY_PROPOSAL_DIR = path.join(REPO_ROOT, "ai-service/data/proposals");
const SUPPORTED_RFP_EXTENSIONS = new Set([".pdf", ".docx", ".pptx"]);

interface RequirementRow {
  req_id: string;
  description: string | null;
  type: string | null;
  mandatory: number;
}

interface ResponseRow {
  requirement_id: string;
  response: string | null;
  status: string | null;
  evidence: string | null;
  review_required: number;
}

function normalizeWebsiteUrl(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "";

  let url: URL;
  try {
    url = new URL(trimmed);
  } catch {
    throw new Error("Website URL is invalid");
  }

  if (!["http:", "https:"].includes(url.protocol)) {
    throw new Error("Website URL must use HTTP or HTTPS");
  }
  if (url.username || url.password) {
    throw new Error("Website URL must not contain credentials");
  }

  url.hash = "";
  return url.toString();
}

function resolveProposalFile(rfpId: string, ext: string): string | null {
  const filename = `${rfpId}_proposal.${ext}`;
  const candidates = [
    path.join(PROPOSAL_DIR, filename),
    path.join(LEGACY_PROPOSAL_DIR, filename),
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) ?? null;
}

export async function rfpRoutes(app: FastifyInstance) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });

  app.post("/api/rfps", async (request, reply) => {
    const rfpId = uuidv4();
    let filename = "";
    let filePath = "";
    let websiteUrl = "";
    let customer = "";
    let industry = "";
    let fileCount = 0;

    try {
      for await (const part of request.parts()) {
        if (part.type === "file") {
          fileCount += 1;
          if (fileCount > 1) {
            part.file.resume();
            continue;
          }

          filename = path.basename(part.filename);
          const extension = path.extname(filename).toLowerCase();
          if (!SUPPORTED_RFP_EXTENSIONS.has(extension)) {
            part.file.resume();
            return reply
              .status(415)
              .send({ error: "Only PDF, DOCX, and PPTX files are supported" });
          }

          filePath = path.join(UPLOAD_DIR, `${rfpId}_${filename}`);
          fs.writeFileSync(filePath, await part.toBuffer());
          continue;
        }

        const value = String(part.value ?? "");
        if (part.fieldname === "customer") customer = value.trim();
        if (part.fieldname === "industry") industry = value.trim();
        if (part.fieldname === "website_url") websiteUrl = value;
      }

      websiteUrl = normalizeWebsiteUrl(websiteUrl);
    } catch (err) {
      if (filePath && fs.existsSync(filePath)) fs.unlinkSync(filePath);
      const message = err instanceof Error ? err.message : "Invalid upload";
      return reply.status(400).send({ error: message });
    }

    if (fileCount > 1) {
      if (filePath && fs.existsSync(filePath)) fs.unlinkSync(filePath);
      return reply.status(400).send({ error: "Upload only one document" });
    }
    if (!filePath && !websiteUrl) {
      return reply
        .status(400)
        .send({ error: "Provide a document or a website URL" });
    }

    if (!filename) {
      filename = `Website - ${new URL(websiteUrl).hostname}`;
    }

    db.prepare(
      `INSERT INTO rfps
       (id, filename, file_path, website_url, customer, industry, status)
       VALUES (?, ?, ?, ?, ?, ?, 'uploaded')`
    ).run(rfpId, filename, filePath, websiteUrl || null, customer, industry);

    db.prepare(
      `INSERT INTO audit_log (rfp_id, action, details) VALUES (?, ?, ?)`
    ).run(
      rfpId,
      "upload",
      JSON.stringify({ filename: filePath ? filename : null, websiteUrl: websiteUrl || null })
    );

    return { id: rfpId, filename, websiteUrl: websiteUrl || null, status: "uploaded" };
  });

  app.get("/api/rfps/:id", async (request) => {
    const { id } = request.params as { id: string };
    const rfp = db.prepare("SELECT * FROM rfps WHERE id = ?").get(id);
    if (!rfp) return { error: "Not found" };

    const requirements = db
      .prepare("SELECT * FROM requirements WHERE rfp_id = ?")
      .all(id);
    const responses = db
      .prepare("SELECT * FROM responses WHERE rfp_id = ?")
      .all(id);

    return { rfp, requirements, responses };
  });

  app.post("/api/rfps/:id/analyze", async (request, reply) => {
    const { id } = request.params as { id: string };
    const rfp = db.prepare("SELECT * FROM rfps WHERE id = ?").get(id) as
      | { file_path: string; website_url: string | null }
      | undefined;

    if (!rfp) return reply.status(404).send({ error: "RFP not found" });

    db.prepare("UPDATE rfps SET status = 'analyzing' WHERE id = ?").run(id);

    try {
      const result = await analyzeRfp(
        rfp.file_path || undefined,
        rfp.website_url || undefined
      );

      db.prepare("DELETE FROM requirements WHERE rfp_id = ?").run(id);
      const insertReq = db.prepare(
        `INSERT INTO requirements (id, rfp_id, req_id, description, type, mandatory, source_section)
         VALUES (?, ?, ?, ?, ?, ?, ?)`
      );

      for (const req of result.requirements) {
        insertReq.run(
          uuidv4(),
          id,
          req.id,
          req.description,
          req.type,
          req.mandatory ? 1 : 0,
          req.source_section || ""
        );
      }

      db.prepare(
        `UPDATE rfps SET status = 'analyzed', metadata = ?, updated_at = datetime('now') WHERE id = ?`
      ).run(JSON.stringify(result.metadata), id);

      return {
        metadata: result.metadata,
        requirements: result.requirements,
        count: result.requirements.length,
      };
    } catch (err) {
      db.prepare("UPDATE rfps SET status = 'error' WHERE id = ?").run(id);
      throw err;
    }
  });

  function savePipelineResult(
    id: string,
    result: {
      metadata: Record<string, unknown>;
      requirements: Array<Record<string, unknown>>;
      responses: Array<Record<string, unknown>>;
      compliance?: Record<string, unknown>;
    }
  ) {
    db.prepare("DELETE FROM requirements WHERE rfp_id = ?").run(id);
    db.prepare("DELETE FROM responses WHERE rfp_id = ?").run(id);

    const insertReq = db.prepare(
      `INSERT INTO requirements (id, rfp_id, req_id, description, type, mandatory, source_section)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    );
    const insertResp = db.prepare(
      `INSERT INTO responses (id, rfp_id, requirement_id, response, status, confidence, evidence, review_required, model_used)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
    );

    for (const req of result.requirements) {
      insertReq.run(
        uuidv4(),
        id,
        req.id,
        req.description,
        req.type,
        req.mandatory ? 1 : 0,
        req.source_section || ""
      );
    }

    for (const resp of result.responses) {
      insertResp.run(
        uuidv4(),
        id,
        resp.requirementId,
        resp.response,
        resp.status,
        resp.confidence || 0,
        JSON.stringify(resp.evidence || []),
        resp.reviewRequired ? 1 : 0,
        process.env.LLM_MODEL || "qwen3:8b"
      );
    }

    const metadata = {
      ...result.metadata,
      compliance: result.compliance ?? null,
    };

    db.prepare(
      `UPDATE rfps SET status = 'completed', metadata = ?, updated_at = datetime('now') WHERE id = ?`
    ).run(JSON.stringify(metadata), id);
  }

  async function executePipeline(
    id: string,
    filePath: string,
    websiteUrl: string,
    industry: string
  ) {
    const filters = {
      approved: true,
      industry: industry || undefined,
    };

    try {
      const result = await runPipeline(filePath || undefined, websiteUrl || undefined, filters, id);
      savePipelineResult(id, result);
      setPipelineJob(id, {
        status: "completed",
        compliance: result.compliance as Record<string, unknown>,
      });
    } catch (err) {
      db.prepare("UPDATE rfps SET status = 'error' WHERE id = ?").run(id);
      const message = err instanceof Error ? err.message : "Pipeline failed";
      setPipelineJob(id, { status: "error", error: message });
    }
  }

  app.post("/api/rfps/:id/pipeline", async (request, reply) => {
    const { id } = request.params as { id: string };
    const rfp = db.prepare("SELECT * FROM rfps WHERE id = ?").get(id) as
      | { file_path: string; website_url: string | null; industry: string }
      | undefined;

    if (!rfp) return reply.status(404).send({ error: "RFP not found" });

    const existing = getPipelineJob(id);
    if (existing.status === "running") {
      return reply.status(409).send({ error: "Pipeline already running" });
    }

    db.prepare("UPDATE rfps SET status = 'processing' WHERE id = ?").run(id);
    setPipelineJob(id, { status: "running" });

    void executePipeline(id, rfp.file_path, rfp.website_url || "", rfp.industry);

    return { status: "started", rfpId: id };
  });

  app.get("/api/rfps/:id/pipeline/status", async (request, reply) => {
    const { id } = request.params as { id: string };
    const rfp = db.prepare("SELECT id FROM rfps WHERE id = ?").get(id);
    if (!rfp) return reply.status(404).send({ error: "RFP not found" });

    const job = getPipelineJob(id);

    if (job.status === "running") {
      try {
        const progress = await getPipelineProgress(id);
        return { ...job, progress };
      } catch {
        return job;
      }
    }

    if (job.status === "completed") {
      return { ...job, progress: { status: "completed", percent: 100 } };
    }

    return job;
  });

  app.get("/api/rfps/:id/requirements", async (request) => {
    const { id } = request.params as { id: string };
    const requirements = db
      .prepare("SELECT * FROM requirements WHERE rfp_id = ?")
      .all(id) as RequirementRow[];
    const responses = db
      .prepare("SELECT * FROM responses WHERE rfp_id = ?")
      .all(id) as ResponseRow[];

    const responseMap = Object.fromEntries(
      responses.map((r) => [
        r.requirement_id,
        r,
      ])
    );

    return requirements.map((req) => ({
      ...req,
      response: responseMap[req.req_id] || null,
    }));
  });

  app.post("/api/rfps/:id/review", async (request) => {
    const { id } = request.params as { id: string };
    const body = request.body as {
      requirementId: string;
      action: "accept" | "reject" | "edit";
      response?: string;
    };

    if (body.action === "edit" && body.response) {
      db.prepare(
        `UPDATE responses SET response = ?, review_status = 'edited' WHERE rfp_id = ? AND requirement_id = ?`
      ).run(body.response, id, body.requirementId);
    } else {
      db.prepare(
        `UPDATE responses SET review_status = ? WHERE rfp_id = ? AND requirement_id = ?`
      ).run(body.action === "accept" ? "accepted" : "rejected", id, body.requirementId);
    }

    return { success: true };
  });

  async function executeProposal(id: string) {
    const rfp = db.prepare("SELECT * FROM rfps WHERE id = ?").get(id) as
      | { metadata: string }
      | undefined;

    if (!rfp) {
      setProposalJob(id, { status: "error", error: "RFP not found" });
      return;
    }

    const requirements = db
      .prepare("SELECT * FROM requirements WHERE rfp_id = ?")
      .all(id) as RequirementRow[];
    const responses = db
      .prepare("SELECT * FROM responses WHERE rfp_id = ?")
      .all(id) as ResponseRow[];

    const metadata = rfp.metadata ? JSON.parse(rfp.metadata) : {};
    const formattedReqs = requirements.map((r) => ({
      id: r.req_id,
      description: r.description,
      type: r.type,
      mandatory: r.mandatory === 1,
    }));
    const formattedResps = responses.map((r) => ({
      requirementId: r.requirement_id,
      response: r.response,
      status: r.status,
      evidence: r.evidence ? JSON.parse(r.evidence) : [],
      reviewRequired: r.review_required === 1,
    }));
    const compliance =
      (metadata.compliance as Record<string, unknown> | undefined) ?? {
        complianceMatrix: [],
      };

    try {
      const result = await generateProposal({
        rfp_id: id,
        metadata,
        requirements: formattedReqs,
        responses: formattedResps,
        compliance,
        job_id: id,
      });

      db.prepare("UPDATE rfps SET status = 'proposal_generated' WHERE id = ?").run(
        id
      );

      setProposalJob(id, {
        status: "completed",
        docxPath: result.docxPath,
        pptxPath: result.pptxPath,
        pdfPath: result.pdfPath,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Proposal generation failed";
      setProposalJob(id, { status: "error", error: message });
    }
  }

  app.post("/api/rfps/:id/proposal", async (request, reply) => {
    const { id } = request.params as { id: string };
    const rfp = db.prepare("SELECT id FROM rfps WHERE id = ?").get(id);
    if (!rfp) return reply.status(404).send({ error: "RFP not found" });

    const existing = getProposalJob(id);
    if (existing.status === "running") {
      return reply.status(409).send({ error: "Proposal generation already running" });
    }

    setProposalJob(id, { status: "running" });
    void executeProposal(id);

    return { status: "started", rfpId: id };
  });

  app.get("/api/rfps/:id/proposal/status", async (request, reply) => {
    const { id } = request.params as { id: string };
    const rfp = db.prepare("SELECT id FROM rfps WHERE id = ?").get(id);
    if (!rfp) return reply.status(404).send({ error: "RFP not found" });

    const job = getProposalJob(id);

    if (job.status === "running") {
      try {
        const progress = await getProposalProgress(id);
        return { ...job, progress };
      } catch {
        return job;
      }
    }

    if (job.status === "completed") {
      return { ...job, progress: { status: "completed", percent: 100, step: "complete" } };
    }

    return job;
  });

  app.get("/api/rfps/:id/download/:format", async (request, reply) => {
    const { id, format } = request.params as { id: string; format: string };
    const formatMap: Record<string, { ext: string; mime: string }> = {
      docx: {
        ext: "docx",
        mime: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      },
      pptx: {
        ext: "pptx",
        mime: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      },
      pdf: { ext: "pdf", mime: "application/pdf" },
    };

    const selected = formatMap[format];
    if (!selected) {
      return reply.status(400).send({ error: "Unsupported download format" });
    }

    let filePath = resolveProposalFile(id, selected.ext);

    if (!filePath && format === "pdf") {
      const docxPath = resolveProposalFile(id, "docx");
      if (!docxPath) {
        return reply.status(404).send({ error: "Proposal not found" });
      }

      try {
        const converted = await convertProposalPdf(docxPath);
        filePath =
          converted.pdfPath && fs.existsSync(converted.pdfPath)
            ? converted.pdfPath
            : null;
      } catch {
        filePath = null;
      }

      if (!filePath) {
        return reply.status(503).send({
          error:
            "PDF conversion unavailable. Install LibreOffice (brew install --cask libreoffice) or download DOCX/PPTX instead.",
        });
      }
    }

    if (!filePath) {
      return reply.status(404).send({ error: "Proposal not found" });
    }

    const content = fs.readFileSync(filePath);
    reply.header(
      "Content-Disposition",
      `attachment; filename="proposal-${id}.${selected.ext}"`
    );
    reply.type(selected.mime);
    return content;
  });

  app.post("/api/knowledge/ingest", async (request, reply) => {
    const data = await request.file();
    if (!data) {
      return reply.status(400).send({ error: "No file uploaded" });
    }

    const documentId = uuidv4();
    const filePath = path.join(UPLOAD_DIR, `${documentId}_${data.filename}`);
    fs.writeFileSync(filePath, await data.toBuffer());

    const fields = data.fields as Record<string, { value?: string }>;
    const docId = fields.document_id?.value || documentId;
    const documentType = fields.document_type?.value || "historical";
    const industry = fields.industry?.value || "";
    const year = parseInt(fields.year?.value || "2025", 10);
    const approvalStatus = fields.approval_status?.value || "approved";

    try {
      const result = await ingestKnowledge({
        file_path: filePath,
        document_id: docId,
        document_type: documentType,
        industry,
        year,
        approval_status: approvalStatus,
      });

      db.prepare(
        `INSERT INTO knowledge_documents
         (id, document_id, filename, document_type, industry, year, approval_status, chunks_ingested)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
      ).run(
        documentId,
        result.document_id,
        data.filename,
        documentType,
        industry,
        year,
        approvalStatus,
        result.ingested
      );

      return {
        ...result,
        filename: data.filename,
        document_type: documentType,
        industry,
        year,
        approval_status: approvalStatus,
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : "Ingestion failed";
      return reply.status(502).send({ error: message });
    }
  });

  async function removeKnowledgeDocument(doc: {
    id: string;
    document_id: string;
    filename: string;
  }) {
    let milvusDeleted = 0;
    try {
      const result = await deleteKnowledgeVectors(doc.document_id);
      milvusDeleted = result.deleted;
    } catch {
      // Best-effort Milvus cleanup (e.g. vectors already removed manually in Attu).
    }

    const uploadPath = path.join(UPLOAD_DIR, `${doc.id}_${doc.filename}`);
    if (fs.existsSync(uploadPath)) {
      fs.unlinkSync(uploadPath);
    }

    db.prepare(`DELETE FROM knowledge_documents WHERE id = ?`).run(doc.id);

    return {
      id: doc.id,
      document_id: doc.document_id,
      milvus_chunks_deleted: milvusDeleted,
    };
  }

  app.get("/api/knowledge", async () => {
    const documents = db
      .prepare(
        `SELECT id, document_id, filename, document_type, industry, year,
                approval_status, chunks_ingested, created_at
         FROM knowledge_documents
         ORDER BY created_at DESC`
      )
      .all();
    return { documents };
  });

  app.post("/api/knowledge/bulk-delete", async (request, reply) => {
    const body = request.body as { ids?: string[] };
    const ids = body.ids?.filter(Boolean) ?? [];

    if (ids.length === 0) {
      return reply.status(400).send({ error: "No document ids provided" });
    }

    const deleted: Array<{
      id: string;
      document_id: string;
      milvus_chunks_deleted: number;
    }> = [];
    const notFound: string[] = [];

    for (const id of ids) {
      const doc = db
        .prepare(
          `SELECT id, document_id, filename FROM knowledge_documents WHERE id = ?`
        )
        .get(id) as
        | { id: string; document_id: string; filename: string }
        | undefined;

      if (!doc) {
        notFound.push(id);
        continue;
      }

      deleted.push(await removeKnowledgeDocument(doc));
    }

    return {
      success: true,
      deleted_count: deleted.length,
      deleted,
      not_found: notFound,
    };
  });

  app.delete("/api/knowledge/:id", async (request, reply) => {
    const { id } = request.params as { id: string };
    const doc = db
      .prepare(
        `SELECT id, document_id, filename FROM knowledge_documents WHERE id = ?`
      )
      .get(id) as
      | { id: string; document_id: string; filename: string }
      | undefined;

    if (!doc) {
      return reply.status(404).send({ error: "Document not found" });
    }

    const result = await removeKnowledgeDocument(doc);
    return { success: true, ...result };
  });
}

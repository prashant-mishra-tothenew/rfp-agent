import { FastifyInstance } from "fastify";
import fs from "fs";
import path from "path";
import { v4 as uuidv4 } from "uuid";
import { db } from "../db/index.js";
import {
  analyzeRfp,
  generateProposal,
  ingestKnowledge,
  runPipeline,
} from "../services/ai-client.js";

const UPLOAD_DIR =
  process.env.UPLOAD_DIR || path.join(process.cwd(), "../../data/uploads");

export async function rfpRoutes(app: FastifyInstance) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });

  app.post("/api/rfps", async (request, reply) => {
    const data = await request.file();
    if (!data) {
      return reply.status(400).send({ error: "No file uploaded" });
    }

    const rfpId = uuidv4();
    const filename = data.filename;
    const filePath = path.join(UPLOAD_DIR, `${rfpId}_${filename}`);
    const buffer = await data.toBuffer();
    fs.writeFileSync(filePath, buffer);

    const fields = data.fields as Record<string, { value?: string }>;
    const customer = fields.customer?.value || "";
    const industry = fields.industry?.value || "";

    db.prepare(
      `INSERT INTO rfps (id, filename, file_path, customer, industry, status)
       VALUES (?, ?, ?, ?, ?, 'uploaded')`
    ).run(rfpId, filename, filePath, customer, industry);

    db.prepare(
      `INSERT INTO audit_log (rfp_id, action, details) VALUES (?, ?, ?)`
    ).run(rfpId, "upload", JSON.stringify({ filename }));

    return { id: rfpId, filename, status: "uploaded" };
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
      | { file_path: string }
      | undefined;

    if (!rfp) return reply.status(404).send({ error: "RFP not found" });

    db.prepare("UPDATE rfps SET status = 'analyzing' WHERE id = ?").run(id);

    try {
      const result = await analyzeRfp(rfp.file_path);

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

  app.post("/api/rfps/:id/pipeline", async (request, reply) => {
    const { id } = request.params as { id: string };
    const rfp = db.prepare("SELECT * FROM rfps WHERE id = ?").get(id) as
      | { file_path: string; industry: string }
      | undefined;

    if (!rfp) return reply.status(404).send({ error: "RFP not found" });

    db.prepare("UPDATE rfps SET status = 'processing' WHERE id = ?").run(id);

    const filters = {
      approved: true,
      industry: rfp.industry || undefined,
    };

    try {
      const result = await runPipeline(rfp.file_path, filters);

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
          process.env.LLM_MODEL || "qwen3:32b"
        );
      }

      db.prepare(
        `UPDATE rfps SET status = 'completed', metadata = ?, updated_at = datetime('now') WHERE id = ?`
      ).run(JSON.stringify(result.metadata), id);

      return result;
    } catch (err) {
      db.prepare("UPDATE rfps SET status = 'error' WHERE id = ?").run(id);
      const message = err instanceof Error ? err.message : "Pipeline failed";
      return reply.status(502).send({ error: message });
    }
  });

  app.get("/api/rfps/:id/requirements", async (request) => {
    const { id } = request.params as { id: string };
    const requirements = db
      .prepare("SELECT * FROM requirements WHERE rfp_id = ?")
      .all(id);
    const responses = db
      .prepare("SELECT * FROM responses WHERE rfp_id = ?")
      .all(id);

    const responseMap = Object.fromEntries(
      responses.map((r: { requirement_id: string }) => [
        r.requirement_id,
        r,
      ])
    );

    return requirements.map((req: { req_id: string }) => ({
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

  app.post("/api/rfps/:id/proposal", async (request, reply) => {
    const { id } = request.params as { id: string };
    const rfp = db.prepare("SELECT * FROM rfps WHERE id = ?").get(id) as
      | { metadata: string }
      | undefined;

    if (!rfp) return reply.status(404).send({ error: "RFP not found" });

    const requirements = db
      .prepare("SELECT * FROM requirements WHERE rfp_id = ?")
      .all(id);
    const responses = db
      .prepare("SELECT * FROM responses WHERE rfp_id = ?")
      .all(id);

    const metadata = rfp.metadata ? JSON.parse(rfp.metadata) : {};
    const formattedReqs = requirements.map((r: Record<string, unknown>) => ({
      id: r.req_id,
      description: r.description,
      type: r.type,
      mandatory: r.mandatory === 1,
    }));
    const formattedResps = responses.map((r: Record<string, unknown>) => ({
      requirementId: r.requirement_id,
      response: r.response,
      status: r.status,
      evidence: r.evidence ? JSON.parse(r.evidence as string) : [],
      reviewRequired: r.review_required === 1,
    }));

    const result = await generateProposal({
      rfp_id: id,
      metadata,
      requirements: formattedReqs,
      responses: formattedResps,
      compliance: { complianceMatrix: [] },
    });

    db.prepare("UPDATE rfps SET status = 'proposal_generated' WHERE id = ?").run(
      id
    );

    return result;
  });

  app.get("/api/rfps/:id/download/:format", async (request, reply) => {
    const { id, format } = request.params as { id: string; format: string };
    const proposalDir =
      process.env.PROPOSAL_DIR || path.join(process.cwd(), "../../data/proposals");
    const ext = format === "pdf" ? "pdf" : "docx";
    const filePath = path.join(proposalDir, `${id}_proposal.${ext}`);

    if (!fs.existsSync(filePath)) {
      return reply.status(404).send({ error: "Proposal not found" });
    }

    const content = fs.readFileSync(filePath);
    reply.header(
      "Content-Disposition",
      `attachment; filename="proposal-${id}.${ext}"`
    );
    reply.type(
      ext === "pdf"
        ? "application/pdf"
        : "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    );
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
}

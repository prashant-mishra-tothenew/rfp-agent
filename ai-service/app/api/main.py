import os
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from pymilvus.exceptions import MilvusException

from app.agents.compliance_checker import check_compliance
from app.agents.knowledge_agent import retrieve_knowledge
from app.agents.orchestrator import run_full_pipeline
from app.agents.response_agent import generate_response
from app.agents.rfp_analyzer import analyze_rfp
from app.config import settings
from app.documents.parser import parse_document
from app.proposal.generator import (
    convert_to_pdf,
    generate_proposal_content,
    render_docx,
)
from app.providers.ollama_provider import ollama_provider
from app.rag.milvus_store import milvus_store

app = FastAPI(title="RFP Agent AI Service", version="1.0.0")


class SearchRequest(BaseModel):
    query: str
    filters: dict[str, Any] | None = None
    topK: int = 5


class GenerateResponseRequest(BaseModel):
    requirement: dict[str, Any]
    evidence: list[dict[str, Any]] | None = None
    filters: dict[str, Any] | None = None


class AnalyzeRequest(BaseModel):
    file_path: str


class PipelineRequest(BaseModel):
    file_path: str
    filters: dict[str, Any] | None = None


class IngestRequest(BaseModel):
    file_path: str
    document_id: str
    document_type: str = "historical"
    industry: str = ""
    year: int = 2025
    approval_status: str = "approved"


class ProposalRequest(BaseModel):
    rfp_id: str
    metadata: dict[str, Any]
    requirements: list[dict[str, Any]]
    responses: list[dict[str, Any]]
    compliance: dict[str, Any]


@app.get("/health")
async def health():
    ollama_ok = await ollama_provider.health()
    return {
        "status": "ok" if ollama_ok else "degraded",
        "ollama": ollama_ok,
        "model": settings.llm_model,
        "embedding_model": settings.embedding_model,
    }


@app.post("/ai/rfp/analyze")
async def analyze_rfp_endpoint(req: AnalyzeRequest):
    if not os.path.exists(req.file_path):
        raise HTTPException(404, "File not found")

    parsed = parse_document(req.file_path)
    result = await analyze_rfp(parsed["text"])
    return {
        "metadata": result.get("metadata", {}),
        "requirements": result.get("requirements", []),
        "document": {"filename": parsed["filename"], "format": parsed["format"]},
    }


@app.post("/ai/rfp/pipeline")
async def run_pipeline(req: PipelineRequest):
    """Full multi-agent LangGraph pipeline."""
    if not os.path.exists(req.file_path):
        raise HTTPException(404, "File not found")

    parsed = parse_document(req.file_path)
    try:
        result = await run_full_pipeline(parsed["text"], filters=req.filters)
    except MilvusException as exc:
        raise HTTPException(
            503,
            "Milvus vector database is unavailable. Start it with: "
            "docker compose up -d etcd minio milvus",
        ) from exc
    except httpx.ReadTimeout:
        raise HTTPException(
            504,
            "Ollama request timed out. Try a smaller RFP or ensure Ollama is running with qwen3:8b.",
        )
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Ollama unavailable: {exc}") from exc

    return {
        "metadata": result.get("metadata", {}),
        "requirements": result.get("requirements", []),
        "responses": result.get("responses", []),
        "compliance": result.get("compliance", {}),
        "current_step": result.get("current_step"),
    }


@app.post("/ai/knowledge/search")
async def search_knowledge(req: SearchRequest):
    hits = await milvus_store.search(
        req.query, top_k=req.topK, filters=req.filters
    )
    return {"results": hits}


@app.post("/ai/rfp/generate-response")
async def generate_response_endpoint(req: GenerateResponseRequest):
    evidence = req.evidence
    if evidence is None:
        evidence = await retrieve_knowledge(req.requirement, filters=req.filters)
    return await generate_response(req.requirement, evidence)


class ComplianceRequest(BaseModel):
    requirements: list[dict[str, Any]]
    responses: list[dict[str, Any]]


@app.post("/ai/rfp/compliance")
async def compliance_endpoint(req: ComplianceRequest):
    return check_compliance(req.requirements, req.responses)


@app.post("/ai/knowledge/ingest")
async def ingest_document(req: IngestRequest):
    if not os.path.exists(req.file_path):
        raise HTTPException(404, "File not found")

    parsed = parse_document(req.file_path)
    text = parsed["text"]
    chunk_size = 1500
    chunks = []

    for i in range(0, len(text), chunk_size):
        chunk_text = text[i : i + chunk_size]
        chunks.append(
            {
                "id": str(uuid.uuid4()),
                "document_id": req.document_id,
                "document_type": req.document_type,
                "section": f"chunk-{i // chunk_size + 1}",
                "content": chunk_text,
                "industry": req.industry,
                "technology": "",
                "year": req.year,
                "approval_status": req.approval_status,
                "confidentiality": "internal",
                "source_page": i // chunk_size + 1,
            }
        )

    count = await milvus_store.insert_chunks(chunks)
    return {"ingested": count, "document_id": req.document_id}


@app.post("/ai/proposal/generate")
async def generate_proposal(req: ProposalRequest):
    proposal = await generate_proposal_content(
        req.metadata, req.requirements, req.responses, req.compliance
    )
    proposal["customer"] = req.metadata.get("customer", "")

    docx_path = os.path.join(
        settings.proposal_dir, f"{req.rfp_id}_proposal.docx"
    )
    render_docx(proposal, docx_path, req.rfp_id)
    pdf_path = convert_to_pdf(docx_path)

    return {
        "proposal": proposal,
        "docxPath": docx_path,
        "pdfPath": pdf_path,
    }


@app.post("/ai/documents/parse")
async def parse_doc(file: UploadFile = File(...)):
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, file.filename or "upload")
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    parsed = parse_document(file_path)
    return {"file_path": file_path, **parsed}

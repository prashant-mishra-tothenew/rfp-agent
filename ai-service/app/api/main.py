import os
import uuid
from pathlib import Path
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
from app.documents.website_crawler import WebsiteCrawlError, crawl_website
from app.proposal.generator import build_proposal_files, convert_to_pdf
from app.pipeline.progress import complete_job, fail_job, get_job, init_job, update_job
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
    file_path: str | None = None
    website_url: str | None = None


class PipelineRequest(BaseModel):
    file_path: str | None = None
    website_url: str | None = None
    filters: dict[str, Any] | None = None
    job_id: str | None = None


class IngestRequest(BaseModel):
    file_path: str
    document_id: str
    document_type: str = "historical"
    industry: str = ""
    year: int = 2025
    approval_status: str = "approved"


class DeleteKnowledgeRequest(BaseModel):
    document_id: str


class ProposalRequest(BaseModel):
    rfp_id: str
    metadata: dict[str, Any]
    requirements: list[dict[str, Any]]
    responses: list[dict[str, Any]]
    compliance: dict[str, Any]
    job_id: str | None = None


class ConvertPdfRequest(BaseModel):
    docx_path: str


def _parse_uploaded_document(file_path: str) -> dict[str, Any]:
    upload_dir = Path(settings.upload_dir).resolve()
    candidate = Path(file_path).resolve()
    if not candidate.is_relative_to(upload_dir):
        raise ValueError("Document path is outside the upload directory")
    if not candidate.is_file():
        raise FileNotFoundError("Uploaded document was not found")
    return parse_document(str(candidate))


async def _collect_analysis_sources(
    file_path: str | None,
    website_url: str | None,
    job_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    if not file_path and not website_url:
        raise ValueError("Provide a document or a website URL")

    source_parts: list[str] = []
    source_metadata: dict[str, Any] = {}

    if file_path:
        parsed = _parse_uploaded_document(file_path)
        source_parts.append(
            f"=== UPLOADED DOCUMENT: {parsed['filename']} ===\n{parsed['text']}"
        )
        source_metadata["document"] = {
            "filename": parsed["filename"],
            "format": parsed["format"],
        }

    if website_url:
        update_job(
            job_id,
            percent=2,
            step="crawler",
            message="Crawling website pages and identifying visible features...",
        )
        crawled = await crawl_website(website_url)
        source_parts.append(
            f"=== WEBSITE SOURCE: {crawled.start_url} ===\n{crawled.text}"
        )
        source_metadata["website"] = {
            "url": crawled.start_url,
            "pages_crawled": len(crawled.pages),
            "warnings": crawled.warnings,
        }

    return "\n\n".join(source_parts), source_metadata


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
    try:
        source_text, sources = await _collect_analysis_sources(
            req.file_path, req.website_url
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, WebsiteCrawlError) as exc:
        raise HTTPException(422, str(exc)) from exc

    result = await analyze_rfp(source_text)
    return {
        "metadata": result.get("metadata", {}),
        "requirements": result.get("requirements", []),
        "sources": sources,
    }


@app.post("/ai/rfp/pipeline")
async def run_pipeline(req: PipelineRequest):
    """Full multi-agent LangGraph pipeline."""
    if req.job_id:
        init_job(req.job_id)
    try:
        source_text, sources = await _collect_analysis_sources(
            req.file_path, req.website_url, req.job_id
        )
        result = await run_full_pipeline(
            source_text, filters=req.filters, job_id=req.job_id
        )
        result_metadata = result.setdefault("metadata", {})
        result_metadata["sources"] = sources
    except FileNotFoundError as exc:
        fail_job(req.job_id, str(exc))
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, WebsiteCrawlError) as exc:
        fail_job(req.job_id, str(exc))
        raise HTTPException(422, str(exc)) from exc
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


@app.get("/ai/rfp/pipeline/progress/{job_id}")
async def pipeline_progress(job_id: str):
    return get_job(job_id)


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

    try:
        parsed = parse_document(req.file_path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    text = (parsed.get("text") or "").strip()
    if not text:
        raise HTTPException(
            400,
            "No extractable text found in document. "
            "Ensure the file is not empty or image-only.",
        )

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

    try:
        count = await milvus_store.insert_chunks(chunks)
    except MilvusException as exc:
        raise HTTPException(
            503,
            "Milvus vector database is unavailable. Start it with: "
            "docker compose up -d etcd minio milvus",
        ) from exc

    return {"ingested": count, "document_id": req.document_id}


@app.post("/ai/knowledge/delete")
async def delete_knowledge(req: DeleteKnowledgeRequest):
    try:
        deleted = milvus_store.delete_by_document_id(req.document_id)
    except MilvusException as exc:
        raise HTTPException(
            503,
            "Milvus vector database is unavailable. Start it with: "
            "docker compose up -d etcd minio milvus",
        ) from exc
    return {"deleted": deleted, "document_id": req.document_id}


def _proposal_progress(job_id: str | None, **fields: Any) -> None:
    update_job(job_id, **fields)


@app.post("/ai/proposal/generate")
async def generate_proposal(req: ProposalRequest):
    if req.job_id:
        init_job(req.job_id)

    try:
        result = await build_proposal_files(
            req.rfp_id,
            req.metadata,
            req.requirements,
            req.responses,
            req.compliance,
            on_progress=lambda **fields: _proposal_progress(req.job_id, **fields),
        )
        complete_job(req.job_id)
        return result
    except httpx.HTTPError as exc:
        fail_job(req.job_id, f"Ollama unavailable: {exc}")
        raise HTTPException(502, f"Ollama unavailable: {exc}") from exc
    except Exception as exc:
        fail_job(req.job_id, str(exc))
        raise HTTPException(500, f"Proposal generation failed: {exc}") from exc


@app.get("/ai/proposal/progress/{job_id}")
async def proposal_progress(job_id: str):
    return get_job(job_id)


def _validate_proposal_docx_path(docx_path: str) -> str:
    resolved = Path(docx_path).resolve()
    project_root = Path(__file__).resolve().parents[3]
    allowed_roots = [
        Path(settings.proposal_dir).resolve(),
        project_root / "data" / "proposals",
        project_root / "ai-service" / "data" / "proposals",
    ]
    if not any(resolved.is_relative_to(root.resolve()) for root in allowed_roots):
        raise HTTPException(400, "Invalid proposal path")

    if not resolved.exists():
        raise HTTPException(404, "DOCX proposal not found")

    return str(resolved)


@app.post("/ai/proposal/convert-pdf")
async def convert_proposal_pdf(req: ConvertPdfRequest):
    docx_path = _validate_proposal_docx_path(req.docx_path)
    pdf_path = convert_to_pdf(docx_path, force=True)
    if not pdf_path:
        raise HTTPException(
            503,
            "PDF conversion unavailable. Install LibreOffice "
            "(brew install --cask libreoffice) or download DOCX/PPTX instead.",
        )
    return {"pdfPath": pdf_path}


@app.post("/ai/documents/parse")
async def parse_doc(file: UploadFile = File(...)):
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, file.filename or "upload")
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    parsed = parse_document(file_path)
    return {"file_path": file_path, **parsed}

"""LangGraph multi-agent orchestration for RFP processing."""

import asyncio
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.compliance_checker import check_compliance
from app.agents.knowledge_agent import retrieve_knowledge
from app.agents.response_agent import generate_response
from app.agents.rfp_analyzer import analyze_rfp
from app.config import settings
from app.embeddings.service import clear_embedding_cache
from app.pipeline.progress import complete_job, fail_job, update_job


class RFPWorkflowState(TypedDict, total=False):
    document_text: str
    filters: dict[str, Any]
    job_id: str | None
    metadata: dict[str, Any]
    requirements: list[dict[str, Any]]
    evidence_map: dict[str, list[dict[str, Any]]]
    responses: list[dict[str, Any]]
    compliance: dict[str, Any]
    current_step: str
    error: str | None


def _progress(job_id: str | None, percent: int, step: str, message: str, **extra: Any) -> None:
    update_job(job_id, percent=percent, step=step, message=message, **extra)


async def analyzer_node(state: RFPWorkflowState) -> RFPWorkflowState:
    """Agent 1: RFP Analyzer — extract requirements."""
    job_id = state.get("job_id")
    _progress(job_id, 5, "analyzer", "Extracting requirements from RFP...")

    result = await analyze_rfp(state["document_text"])
    requirements = result.get("requirements", [])

    max_reqs = settings.pipeline_max_requirements
    if len(requirements) > max_reqs:
        requirements = requirements[:max_reqs]

    _progress(
        job_id,
        15,
        "analyzer",
        f"Found {len(requirements)} requirements",
        requirementTotal=len(requirements),
        requirementDone=0,
    )

    return {
        **state,
        "metadata": result.get("metadata", {}),
        "requirements": requirements,
        "current_step": "analyzed",
    }


async def knowledge_node(state: RFPWorkflowState) -> RFPWorkflowState:
    """Agent 2: Knowledge Agent — retrieve evidence per requirement (parallel)."""
    job_id = state.get("job_id")
    filters = state.get("filters", {})
    requirements = state.get("requirements", [])
    total = len(requirements) or 1
    done = 0
    sem = asyncio.Semaphore(settings.pipeline_concurrency)

    async def process_one(req: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
        nonlocal done
        req_id = req.get("id", "")
        async with sem:
            evidence = await retrieve_knowledge(req, filters=filters)
            done += 1
            percent = 15 + int((done / total) * 35)
            _progress(
                job_id,
                percent,
                "knowledge",
                f"Retrieving evidence ({done}/{total})",
                requirementDone=done,
            )
            return req_id, evidence

    pairs = await asyncio.gather(*[process_one(req) for req in requirements])
    evidence_map = dict(pairs)

    return {**state, "evidence_map": evidence_map, "current_step": "retrieved"}


async def response_node(state: RFPWorkflowState) -> RFPWorkflowState:
    """Agent 3: Response Agent — generate evidence-backed responses (parallel)."""
    job_id = state.get("job_id")
    evidence_map = state.get("evidence_map", {})
    requirements = state.get("requirements", [])
    total = len(requirements) or 1
    done = 0
    sem = asyncio.Semaphore(settings.pipeline_concurrency)

    async def process_one(req: dict[str, Any]) -> dict[str, Any]:
        nonlocal done
        req_id = req.get("id", "")
        evidence = evidence_map.get(req_id, [])
        async with sem:
            response = await generate_response(req, evidence)
            done += 1
            percent = 50 + int((done / total) * 40)
            _progress(
                job_id,
                percent,
                "response",
                f"Drafting responses ({done}/{total})",
                requirementDone=done,
            )
            return response

    responses = await asyncio.gather(*[process_one(req) for req in requirements])

    return {**state, "responses": list(responses), "current_step": "generated"}


async def compliance_node(state: RFPWorkflowState) -> RFPWorkflowState:
    """Deterministic compliance check after agent generation."""
    job_id = state.get("job_id")
    _progress(job_id, 95, "compliance", "Running compliance check...")

    compliance = check_compliance(
        state.get("requirements", []),
        state.get("responses", []),
    )
    return {**state, "compliance": compliance, "current_step": "complete"}


def build_rfp_workflow() -> StateGraph:
    """Build the LangGraph multi-agent workflow."""
    workflow = StateGraph(RFPWorkflowState)

    workflow.add_node("analyzer", analyzer_node)
    workflow.add_node("knowledge", knowledge_node)
    workflow.add_node("response", response_node)
    workflow.add_node("compliance_check", compliance_node)

    workflow.set_entry_point("analyzer")
    workflow.add_edge("analyzer", "knowledge")
    workflow.add_edge("knowledge", "response")
    workflow.add_edge("response", "compliance_check")
    workflow.add_edge("compliance_check", END)

    return workflow


rfp_workflow = build_rfp_workflow().compile()


async def run_full_pipeline(
    document_text: str,
    filters: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Execute the full multi-agent RFP pipeline."""
    clear_embedding_cache()

    initial_state: RFPWorkflowState = {
        "document_text": document_text,
        "filters": filters or {"approved": True},
        "job_id": job_id,
        "current_step": "starting",
    }

    try:
        result = await rfp_workflow.ainvoke(initial_state)
        complete_job(job_id)
        return dict(result)
    except Exception as exc:
        fail_job(job_id, str(exc))
        raise

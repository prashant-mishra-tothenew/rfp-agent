"""LangGraph multi-agent orchestration for RFP processing."""

import asyncio
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.compliance_checker import check_compliance
from app.agents.knowledge_agent import retrieve_knowledge
from app.agents.response_agent import generate_responses_batch
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
    _progress(job_id, 5, "analyzer", "Preparing document for analysis...")

    stop_heartbeat = asyncio.Event()

    async def heartbeat() -> None:
        if "=== WEBSITE SOURCE:" in state["document_text"]:
            messages = [
                "Extracting website modules and features with local AI (typically 4–7 min)...",
                "Reviewing forms, filters, calendars, media, downloads, and account actions...",
                "Building an exhaustive feature requirement list...",
            ]
        else:
            messages = [
                "Extracting requirements with AI (typically 1–3 min on local hardware)...",
                "Still reading the RFP — large documents take longer...",
                "Almost done with requirement extraction...",
            ]
        tick = 0
        while not stop_heartbeat.is_set():
            _progress(
                job_id,
                min(14, 6 + tick % 4),
                "analyzer",
                messages[tick % len(messages)],
            )
            tick += 1
            try:
                await asyncio.wait_for(stop_heartbeat.wait(), timeout=12.0)
            except asyncio.TimeoutError:
                continue

    heartbeat_task = asyncio.create_task(heartbeat())
    try:
        result = await analyze_rfp(state["document_text"])
    finally:
        stop_heartbeat.set()
        await heartbeat_task

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
            source_type = str(req.get("source_type", "")).lower()
            source_section = str(req.get("source_section", "")).lower()
            is_website_feature = (
                source_type == "website"
                or "website" in source_section
                or "http://" in source_section
                or "https://" in source_section
            )
            evidence = (
                []
                if is_website_feature
                else await retrieve_knowledge(req, filters=filters)
            )
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
    """Agent 3: Response Agent — batched + parallel draft responses."""
    job_id = state.get("job_id")
    evidence_map = state.get("evidence_map", {})
    requirements = state.get("requirements", [])
    total = len(requirements) or 1
    batch_size = max(1, settings.response_batch_size)
    done = 0
    sem = asyncio.Semaphore(settings.pipeline_concurrency)

    batches: list[list[dict[str, Any]]] = [
        requirements[i : i + batch_size]
        for i in range(0, len(requirements), batch_size)
    ]

    async def process_batch(batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nonlocal done
        async with sem:
            items = [
                (req, evidence_map.get(req.get("id", ""), [])) for req in batch
            ]
            batch_responses = await generate_responses_batch(items)
            done += len(batch_responses)
            percent = 50 + int((done / total) * 40)
            _progress(
                job_id,
                percent,
                "response",
                f"Drafting responses ({done}/{total})",
                requirementDone=done,
            )
            return batch_responses

    batch_results = await asyncio.gather(*[process_batch(b) for b in batches])
    responses = [resp for group in batch_results for resp in group]

    return {**state, "responses": responses, "current_step": "generated"}


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

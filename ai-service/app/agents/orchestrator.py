"""LangGraph multi-agent orchestration for RFP processing."""

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.config import settings
from app.agents.compliance_checker import check_compliance
from app.agents.knowledge_agent import retrieve_knowledge
from app.agents.response_agent import generate_response
from app.agents.rfp_analyzer import analyze_rfp


class RFPWorkflowState(TypedDict, total=False):
    document_text: str
    filters: dict[str, Any]
    metadata: dict[str, Any]
    requirements: list[dict[str, Any]]
    evidence_map: dict[str, list[dict[str, Any]]]
    responses: list[dict[str, Any]]
    compliance: dict[str, Any]
    current_step: str
    error: str | None


async def analyzer_node(state: RFPWorkflowState) -> RFPWorkflowState:
    """Agent 1: RFP Analyzer — extract requirements."""
    result = await analyze_rfp(state["document_text"])
    requirements = result.get("requirements", [])

    max_reqs = settings.pipeline_max_requirements
    if len(requirements) > max_reqs:
        requirements = requirements[:max_reqs]

    return {
        **state,
        "metadata": result.get("metadata", {}),
        "requirements": requirements,
        "current_step": "analyzed",
    }


async def knowledge_node(state: RFPWorkflowState) -> RFPWorkflowState:
    """Agent 2: Knowledge Agent — retrieve evidence per requirement."""
    evidence_map: dict[str, list[dict[str, Any]]] = {}
    filters = state.get("filters", {})

    for req in state.get("requirements", []):
        req_id = req.get("id", "")
        evidence = await retrieve_knowledge(req, filters=filters)
        evidence_map[req_id] = evidence

    return {**state, "evidence_map": evidence_map, "current_step": "retrieved"}


async def response_node(state: RFPWorkflowState) -> RFPWorkflowState:
    """Agent 3: Response Agent — generate evidence-backed responses."""
    responses: list[dict[str, Any]] = []
    evidence_map = state.get("evidence_map", {})

    for req in state.get("requirements", []):
        req_id = req.get("id", "")
        evidence = evidence_map.get(req_id, [])
        response = await generate_response(req, evidence)
        responses.append(response)

    return {**state, "responses": responses, "current_step": "generated"}


async def compliance_node(state: RFPWorkflowState) -> RFPWorkflowState:
    """Deterministic compliance check after agent generation."""
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
) -> dict[str, Any]:
    """Execute the full multi-agent RFP pipeline."""
    initial_state: RFPWorkflowState = {
        "document_text": document_text,
        "filters": filters or {"approved": True},
        "current_step": "starting",
    }
    result = await rfp_workflow.ainvoke(initial_state)
    return dict(result)

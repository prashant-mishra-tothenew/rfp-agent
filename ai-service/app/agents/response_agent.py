from typing import Any

from app.config import settings
from app.providers.ollama_provider import ollama_provider

RESPONSE_SYSTEM = """You are a Response Agent for RFP proposals. Generate concise, evidence-backed draft responses.
Rules: Use ONLY provided evidence. Do not invent capabilities. Mark status as SUPPORTED, PARTIALLY_SUPPORTED, NOT_SUPPORTED, or HUMAN_VERIFICATION_REQUIRED.
Return valid JSON only."""

RESPONSE_USER = """Requirement {req_id} ({req_type}, mandatory={mandatory}):
{req_text}

Evidence:
{evidence_text}

Return JSON for this requirement:
{{"requirementId": "{req_id}", "response": "...", "status": "SUPPORTED|PARTIALLY_SUPPORTED|NOT_SUPPORTED|HUMAN_VERIFICATION_REQUIRED", "confidence": 0.0-1.0, "evidence": ["source"], "reviewRequired": true/false, "gaps": []}}"""

RESPONSE_BATCH_USER = """Draft evidence-backed responses for each requirement below.

{blocks}

Return JSON:
{{"responses": [{{"requirementId": "...", "response": "...", "status": "...", "confidence": 0.0, "evidence": [], "reviewRequired": true, "gaps": []}}]}}"""

_NO_EVIDENCE = {
    "response": "No reliable company evidence found for this requirement.",
    "status": "HUMAN_VERIFICATION_REQUIRED",
    "confidence": 0.0,
    "evidence": [],
    "reviewRequired": True,
    "gaps": ["No matching historical knowledge in the knowledge base"],
}


def _format_evidence(evidence: list[dict[str, Any]]) -> tuple[str, list[str]]:
    max_items = settings.response_evidence_items
    max_chars = settings.response_evidence_chars
    lines: list[str] = []
    refs: list[str] = []
    for i, ev in enumerate(evidence[:max_items], 1):
        source = ev.get("document_id") or f"doc-{i}"
        content = (ev.get("content") or "")[:max_chars]
        lines.append(f"[{i}] {source}: {content}")
        refs.append(source)
    return "\n".join(lines), refs


def _no_evidence_response(req_id: str) -> dict[str, Any]:
    return {"requirementId": req_id, **_NO_EVIDENCE}


def _normalize_response(
    result: dict[str, Any], req_id: str, evidence_refs: list[str]
) -> dict[str, Any]:
    result["requirementId"] = req_id
    if not result.get("evidence"):
        result["evidence"] = list(set(evidence_refs))
    return result


async def generate_response(
    requirement: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    req_id = requirement.get("id", "REQ-UNKNOWN")
    if not evidence:
        return _no_evidence_response(req_id)

    req_text = requirement.get("description") or requirement.get("text", "")
    req_type = requirement.get("type", "Technical")
    mandatory = requirement.get("mandatory", True)
    evidence_text, evidence_refs = _format_evidence(evidence)

    content = await ollama_provider.chat(
        messages=[
            {"role": "system", "content": RESPONSE_SYSTEM},
            {
                "role": "user",
                "content": RESPONSE_USER.format(
                    req_id=req_id,
                    req_text=req_text,
                    req_type=req_type,
                    mandatory=mandatory,
                    evidence_text=evidence_text,
                ),
            },
        ],
        model=settings.response_model or settings.llm_fast_model,
        format_json=True,
        temperature=0.1,
        disable_thinking=True,
        max_tokens=settings.response_max_tokens,
    )

    try:
        result = ollama_provider.parse_json_response(content)
        return _normalize_response(result, req_id, evidence_refs)
    except (ValueError, TypeError):
        return {
            "requirementId": req_id,
            "response": "Unable to generate response. Human review required.",
            "status": "HUMAN_VERIFICATION_REQUIRED",
            "confidence": 0.0,
            "evidence": evidence_refs,
            "reviewRequired": True,
            "gaps": ["LLM response parsing failed"],
        }


async def generate_responses_batch(
    items: list[tuple[dict[str, Any], list[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    """Generate responses for multiple requirements in one LLM call."""
    if not items:
        return []

    if len(items) == 1:
        req, evidence = items[0]
        return [await generate_response(req, evidence)]

    blocks: list[str] = []
    evidence_by_id: dict[str, list[str]] = {}
    results: dict[str, dict[str, Any]] = {}

    for req, evidence in items:
        req_id = req.get("id", "REQ-UNKNOWN")
        if not evidence:
            results[req_id] = _no_evidence_response(req_id)
            continue

        req_text = req.get("description") or req.get("text", "")
        req_type = req.get("type", "Technical")
        mandatory = req.get("mandatory", True)
        evidence_text, evidence_refs = _format_evidence(evidence)
        evidence_by_id[req_id] = evidence_refs
        blocks.append(
            f"--- {req_id} ({req_type}, mandatory={mandatory}) ---\n"
            f"{req_text}\n\nEvidence:\n{evidence_text}"
        )

    if not blocks:
        return [_no_evidence_response(req.get("id", "REQ-UNKNOWN")) for req, _ in items]

    content = await ollama_provider.chat(
        messages=[
            {"role": "system", "content": RESPONSE_SYSTEM},
            {
                "role": "user",
                "content": RESPONSE_BATCH_USER.format(blocks="\n\n".join(blocks)),
            },
        ],
        model=settings.response_model or settings.llm_fast_model,
        format_json=True,
        temperature=0.1,
        disable_thinking=True,
        max_tokens=settings.response_max_tokens * len(blocks),
    )

    try:
        parsed = ollama_provider.parse_json_response(content)
        batch_results = parsed.get("responses", parsed if isinstance(parsed, list) else [])
        if isinstance(batch_results, list):
            for entry in batch_results:
                req_id = entry.get("requirementId", "")
                if req_id:
                    results[req_id] = _normalize_response(
                        entry, req_id, evidence_by_id.get(req_id, [])
                    )
    except (ValueError, TypeError):
        pass

    ordered: list[dict[str, Any]] = []
    for req, evidence in items:
        req_id = req.get("id", "REQ-UNKNOWN")
        if req_id in results:
            ordered.append(results[req_id])
        else:
            ordered.append(await generate_response(req, evidence))

    return ordered

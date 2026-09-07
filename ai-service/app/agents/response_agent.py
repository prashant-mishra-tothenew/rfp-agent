from typing import Any

from app.config import settings
from app.providers.ollama_provider import ollama_provider

RESPONSE_SYSTEM = """You are a Response Agent for RFP proposals. Generate evidence-backed draft responses.

STRICT RULES:
1. Do NOT invent capabilities, certifications, customer references, SLA commitments, or technical specs
2. Use ONLY the provided evidence for factual claims
3. Adapt historical responses to the current requirement — do not blindly copy
4. If evidence is insufficient, state "Human verification required" and explain what is missing
5. Mark status as: SUPPORTED, PARTIALLY_SUPPORTED, NOT_SUPPORTED, or HUMAN_VERIFICATION_REQUIRED

Return valid JSON only."""

RESPONSE_USER = """Current Requirement:
ID: {req_id}
Description: {req_text}
Type: {req_type}
Mandatory: {mandatory}

Retrieved Evidence:
{evidence_text}

Return JSON:
{{
  "requirementId": "{req_id}",
  "response": "...",
  "status": "SUPPORTED|PARTIALLY_SUPPORTED|NOT_SUPPORTED|HUMAN_VERIFICATION_REQUIRED",
  "confidence": 0.0-1.0,
  "evidence": ["source1", "source2"],
  "reviewRequired": true/false,
  "gaps": ["..."]
}}"""


async def generate_response(
    requirement: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    req_id = requirement.get("id", "REQ-UNKNOWN")
    req_text = requirement.get("description") or requirement.get("text", "")
    req_type = requirement.get("type", "Technical")
    mandatory = requirement.get("mandatory", True)

    if not evidence:
        return {
            "requirementId": req_id,
            "response": "No reliable company evidence found for this requirement.",
            "status": "HUMAN_VERIFICATION_REQUIRED",
            "confidence": 0.0,
            "evidence": [],
            "reviewRequired": True,
            "gaps": ["No matching historical knowledge in the knowledge base"],
        }

    evidence_lines = []
    evidence_refs = []
    for i, ev in enumerate(evidence, 1):
        source = ev.get("document_id") or f"doc-{i}"
        section = ev.get("section", "")
        page = ev.get("source_page", "")
        content = ev.get("content", "")[:1500]
        evidence_lines.append(
            f"[{i}] Source: {source} | Section: {section} | Page: {page}\n{content}"
        )
        evidence_refs.append(source)

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
                    evidence_text="\n\n".join(evidence_lines),
                ),
            },
        ],
        model=settings.llm_model,
        format_json=True,
        temperature=0.1,
    )

    try:
        result = ollama_provider.parse_json_response(content)
        result["requirementId"] = req_id
        if not result.get("evidence"):
            result["evidence"] = list(set(evidence_refs))
        return result
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

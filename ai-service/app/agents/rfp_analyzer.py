import re
import uuid
from typing import Any

from app.config import settings
from app.providers.ollama_provider import ollama_provider

ANALYZER_SYSTEM = """You are an RFP Analyzer agent. Extract structured requirements from RFP documents.
Rules:
- Identify requirement ID, description, type, mandatory/optional status
- Types: Functional, Technical, Security, Compliance, Commercial, Legal, Implementation, Support
- Include evaluation criteria and evidence requested when present
- Include source page/section references
- Return valid JSON only"""

ANALYZER_USER = """Analyze this RFP document and extract all requirements.

Document text:
{document_text}

Return JSON:
{{
  "metadata": {{
    "title": "...",
    "customer": "...",
    "industry": "...",
    "submission_deadline": "...",
    "evaluation_criteria": ["..."]
  }},
  "requirements": [
    {{
      "id": "REQ-001",
      "description": "...",
      "type": "Technical",
      "mandatory": true,
      "evaluation_criteria": "...",
      "evidence_requested": "...",
      "source_section": "..."
    }}
  ]
}}"""

_REQUIREMENT_KEYWORDS = (
    "shall",
    "must",
    "required",
    "requirement",
    "mandatory",
    "scope",
    "technical",
    "functional",
    "compliance",
    "security",
    "deliverable",
    "criteria",
    "specification",
    "provide",
    "support",
    "vendor",
    "proposal",
)


def _split_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    for block in re.split(r"\n{2,}", text):
        block = block.strip()
        if not block:
            continue
        if len(block) > 1500:
            paragraphs.extend(line.strip() for line in block.split("\n") if line.strip())
        else:
            paragraphs.append(block)
    return paragraphs


def prepare_document_for_analysis(text: str, max_chars: int | None = None) -> str:
    """Trim document to requirement-relevant sections for faster, focused extraction."""
    limit = max_chars or settings.analyzer_max_chars
    if len(text) <= limit:
        return text

    paragraphs = _split_paragraphs(text)
    intro = "\n\n".join(paragraphs[:3])[:1500]

    scored: list[tuple[int, str]] = []
    for paragraph in paragraphs:
        lower = paragraph.lower()
        score = sum(1 for kw in _REQUIREMENT_KEYWORDS if kw in lower)
        if re.match(r"^(\d+[\.\)]|[A-Z]-\d+|REQ-?\d+)", paragraph):
            score += 2
        if score > 0:
            scored.append((score, paragraph))

    if not scored:
        return text[:limit]

    scored.sort(key=lambda item: item[0], reverse=True)

    selected: list[str] = []
    total = len(intro) + 2
    for _, paragraph in scored:
        if total + len(paragraph) > limit:
            continue
        selected.append(paragraph)
        total += len(paragraph) + 2

    if not selected:
        return text[:limit]

    return f"{intro}\n\n---\n\n" + "\n\n".join(selected)


async def analyze_rfp(document_text: str) -> dict[str, Any]:
    text = prepare_document_for_analysis(document_text)

    content = await ollama_provider.chat(
        messages=[
            {"role": "system", "content": ANALYZER_SYSTEM},
            {"role": "user", "content": ANALYZER_USER.format(document_text=text)},
        ],
        model=settings.analyzer_model or settings.llm_fast_model,
        format_json=True,
        disable_thinking=True,
    )

    try:
        result = ollama_provider.parse_json_response(content)
    except (ValueError, TypeError):
        result = {"metadata": {}, "requirements": []}

    for i, req in enumerate(result.get("requirements", [])):
        if not req.get("id"):
            req["id"] = f"REQ-{i+1:03d}"

    return result

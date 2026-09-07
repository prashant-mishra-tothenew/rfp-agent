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


async def analyze_rfp(document_text: str) -> dict[str, Any]:
    # Truncate very long documents for the showcase
    text = document_text[:50000]

    content = await ollama_provider.chat(
        messages=[
            {"role": "system", "content": ANALYZER_SYSTEM},
            {"role": "user", "content": ANALYZER_USER.format(document_text=text)},
        ],
        model=settings.llm_model,
        format_json=True,
    )

    try:
        result = ollama_provider.parse_json_response(content)
    except (ValueError, TypeError):
        result = {"metadata": {}, "requirements": []}

    for i, req in enumerate(result.get("requirements", [])):
        if not req.get("id"):
            req["id"] = f"REQ-{i+1:03d}"

    return result

import json
import re
import uuid
from typing import Any

from app.config import settings
from app.providers.ollama_provider import ollama_provider

ANALYZER_SYSTEM = """You are an RFP Analyzer agent. Extract structured requirements from uploaded documents and crawled website pages.
Rules:
- Identify requirement ID, description, type, mandatory/optional status
- Types: Functional, Technical, Security, Compliance, Commercial, Legal, Implementation, Support
- Include evaluation criteria and evidence requested when present
- For website sources, convert visible features and capabilities into Functional or Technical requirements using wording such as "The solution should provide..."
- Be exhaustive for website analysis: identify modules, screens, navigation, account actions, forms, search, filters, carousels, calendars, lists, detail views, media players, downloads, notifications, redirects, and detected third-party integrations
- Return each atomic website feature as a separate requirement; do not combine a whole module into one generic requirement
- Prefix website-derived descriptions with the most likely module or screen name, for example "Race Calendar - Display schedules in grid and list views"
- For a substantial website, return every supported distinct feature (often 40–75 requirements), not only a short summary
- For 20 or more crawled module pages, target at least 45 distinct requirements when the source supports them
- Never put a comma-separated feature list into one description. Split login, registration, password recovery, filtering, search, list, detail, download, and media controls into separate items
- BAD: "Accounts - Provide registration, login, password reset and logout"
- GOOD: four separate requirements for registration, login, password reset, and logout
- A page normally has several features; do not emit only one generic requirement per page
- Keep each description under 18 words and return compact JSON with no commentary
- Do not infer hidden backend behavior, integrations, security controls, or capabilities that are not visible in the supplied website text
- Merge duplicate requirements found in both sources
- Include the document section or compact website URL path (for example "/register") in source_section
- Set source_type to "website", "document", or "both"
- Return valid JSON only"""

ANALYZER_USER = """Analyze the supplied document and/or website content. Extract explicit document requirements and the features visibly present on website pages.

Analysis sources:
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
      "source_section": "...",
      "source_type": "website|document|both"
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
    "feature",
    "capability",
    "product",
    "solution",
    "platform",
    "service",
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


def _compress_website_pages(website_text: str, budget: int) -> str:
    page_sections = [
        section.strip()
        for section in re.split(r"(?=--- WEBSITE PAGE:)", website_text)
        if section.strip()
    ]
    if not page_sections or budget <= 0:
        return ""

    per_page_budget = max(600, budget // len(page_sections))
    prepared_pages: list[str] = []
    for section in page_sections:
        lines = [line.strip() for line in section.splitlines() if line.strip()]

        def priority(item: tuple[int, str]) -> tuple[int, int]:
            index, line = item
            lower = line.lower()
            if line.startswith(("=== WEBSITE", "--- WEBSITE PAGE:", "[UI ", "[Detected ")):
                rank = 0
            elif len(line) <= 100:
                rank = 1
            elif any(keyword in lower for keyword in _REQUIREMENT_KEYWORDS):
                rank = 2
            elif len(line) <= 200:
                rank = 3
            else:
                rank = 4
            return rank, index

        selected: list[str] = []
        used = 0
        for _, line in sorted(enumerate(lines), key=priority):
            if used + len(line) + 1 > per_page_budget:
                continue
            selected.append(line)
            used += len(line) + 1
        if selected:
            prepared_pages.append("\n".join(selected))

    return "\n\n".join(prepared_pages)[:budget]


def _parse_analyzer_output(content: str) -> dict[str, Any]:
    try:
        parsed = ollama_provider.parse_json_response(content)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    match = re.search(r'"requirements"\s*:\s*\[', content)
    if not match:
        return {"metadata": {}, "requirements": []}

    decoder = json.JSONDecoder()
    position = match.end()
    recovered: list[dict[str, Any]] = []
    while position < len(content):
        while position < len(content) and content[position] in " \t\r\n,":
            position += 1
        if position >= len(content) or content[position] == "]":
            break
        try:
            item, position = decoder.raw_decode(content, position)
        except json.JSONDecodeError:
            break
        if isinstance(item, dict):
            recovered.append(item)

    return {"metadata": {}, "requirements": recovered}


def prepare_document_for_analysis(text: str, max_chars: int | None = None) -> str:
    """Trim document to requirement-relevant sections for faster, focused extraction."""
    limit = max_chars or settings.analyzer_max_chars

    website_marker = "=== WEBSITE SOURCE:"
    if website_marker in text:
        document_text, marker, website_text = text.partition(website_marker)
        website_text = marker + website_text
        website_budget = min(
            settings.website_analysis_max_chars,
            limit if not document_text.strip() else int(limit * 0.55),
        )
        document_budget = limit - website_budget - 2 if document_text.strip() else 0
        prepared_document = (
            prepare_document_for_analysis(document_text, document_budget)
            if document_budget
            else ""
        )
        prepared_website = _compress_website_pages(website_text, website_budget)
        return "\n\n".join(
            part for part in (prepared_document, prepared_website) if part
        )[:limit]

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
    website_only = (
        "=== WEBSITE SOURCE:" in document_text
        and "=== UPLOADED DOCUMENT:" not in document_text
    )

    content = await ollama_provider.chat(
        messages=[
            {"role": "system", "content": ANALYZER_SYSTEM},
            {"role": "user", "content": ANALYZER_USER.format(document_text=text)},
        ],
        model=settings.analyzer_model or settings.llm_fast_model,
        format_json=True,
        disable_thinking=True,
        max_tokens=settings.analyzer_max_tokens,
        context_tokens=settings.analyzer_context_tokens,
    )

    result = _parse_analyzer_output(content)

    if not isinstance(result, dict):
        result = {"metadata": {}, "requirements": []}

    requirements = result.get("requirements", [])
    if not isinstance(requirements, list):
        requirements = []

    unique_requirements: list[dict[str, Any]] = []
    seen_descriptions: set[str] = set()
    for req in requirements:
        if not isinstance(req, dict):
            continue
        description = str(req.get("description", "")).strip()
        key = re.sub(r"\W+", " ", description).strip().casefold()
        if not key or key in seen_descriptions:
            continue
        seen_descriptions.add(key)
        unique_requirements.append(req)

    for i, req in enumerate(unique_requirements):
        if not req.get("id"):
            req["id"] = f"REQ-{i+1:03d}"
        if website_only:
            req["source_type"] = "website"

    result["requirements"] = unique_requirements
    return result

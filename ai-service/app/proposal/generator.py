import os
import subprocess
from pathlib import Path
from typing import Any

from docx import Document
from docx.shared import Inches, Pt

from app.config import settings
from app.providers.ollama_provider import ollama_provider

PROPOSAL_SYSTEM = """You are a proposal writer. Generate structured proposal content from reviewed RFP responses.
Use only the provided responses and evidence. Do not invent capabilities.
Return valid JSON only."""


async def generate_proposal_content(
    metadata: dict[str, Any],
    requirements: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    compliance: dict[str, Any],
) -> dict[str, Any]:
    response_summary = []
    for resp in responses[:30]:  # Limit for context
        response_summary.append(
            f"- {resp.get('requirementId')}: {resp.get('response', '')[:300]}"
        )

    content = await ollama_provider.chat(
        messages=[
            {"role": "system", "content": PROPOSAL_SYSTEM},
            {
                "role": "user",
                "content": f"""Create a structured proposal from these reviewed responses.

Customer: {metadata.get('customer', 'Client')}
Industry: {metadata.get('industry', 'General')}

Responses:
{chr(10).join(response_summary)}

Return JSON:
{{
  "executiveSummary": "...",
  "understandingOfRequirements": "...",
  "proposedSolution": "...",
  "technicalApproach": "...",
  "implementationMethodology": "...",
  "supportAndSla": "...",
  "securityCompliance": "...",
  "relevantExperience": "...",
  "caseStudies": "...",
  "assumptions": "..."
}}""",
            },
        ],
        model=settings.llm_model,
        format_json=True,
    )

    try:
        proposal = ollama_provider.parse_json_response(content)
    except (ValueError, TypeError):
        proposal = {
            "executiveSummary": "Proposal generated from reviewed responses.",
            "proposedSolution": "See compliance matrix for details.",
        }

    proposal["complianceMatrix"] = compliance.get("complianceMatrix", [])
    return proposal


def render_docx(proposal: dict[str, Any], output_path: str, rfp_id: str) -> str:
    """Render structured proposal JSON into a DOCX file."""
    template = Path(settings.template_path)
    if template.exists():
        doc = Document(str(template))
    else:
        doc = Document()

    doc.add_heading("RFP Response Proposal", 0)
    doc.add_paragraph(f"RFP Reference: {rfp_id}")
    doc.add_paragraph(f"Customer: {proposal.get('customer', 'N/A')}")

    sections = [
        ("Executive Summary", "executiveSummary"),
        ("Understanding of Requirements", "understandingOfRequirements"),
        ("Proposed Solution", "proposedSolution"),
        ("Technical Approach", "technicalApproach"),
        ("Implementation Methodology", "implementationMethodology"),
        ("Support and SLA", "supportAndSla"),
        ("Security and Compliance", "securityCompliance"),
        ("Relevant Experience", "relevantExperience"),
        ("Case Studies", "caseStudies"),
        ("Assumptions", "assumptions"),
    ]

    for title, key in sections:
        text = proposal.get(key, "")
        if text:
            doc.add_heading(title, level=1)
            doc.add_paragraph(text)

    matrix = proposal.get("complianceMatrix", [])
    if matrix:
        doc.add_heading("Compliance Matrix", level=1)
        table = doc.add_table(rows=1, cols=5)
        table.style = "Table Grid"
        headers = ["Req ID", "Requirement", "Response", "Status", "Review"]
        for i, h in enumerate(headers):
            table.rows[0].cells[i].text = h

        for row in matrix[:100]:
            cells = table.add_row().cells
            cells[0].text = row.get("requirementId", "")
            cells[1].text = (row.get("requirement") or "")[:200]
            cells[2].text = (row.get("response") or "")[:300]
            cells[3].text = row.get("status", "")
            cells[4].text = "Yes" if row.get("reviewRequired") else "No"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path


def convert_to_pdf(docx_path: str) -> str | None:
    """Convert DOCX to PDF using LibreOffice headless."""
    pdf_path = docx_path.replace(".docx", ".pdf")
    try:
        subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                os.path.dirname(docx_path),
                docx_path,
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return pdf_path if os.path.exists(pdf_path) else None
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None

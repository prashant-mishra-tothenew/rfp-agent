import asyncio
import os
import shutil
import subprocess
from functools import partial
from pathlib import Path
from typing import Any, Callable

from docx import Document

from app.config import settings
from app.proposal.pptx_template import render_pptx_from_template
from app.providers.ollama_provider import ollama_provider

PROPOSAL_SYSTEM = """You are a proposal writer. Write concise, professional proposal sections from reviewed RFP responses.
Use only the provided responses. Do not invent capabilities. Return valid JSON only."""

PROPOSAL_BATCHES: list[list[str]] = [
    ["executiveSummary", "understandingOfRequirements", "proposedSolution"],
    ["technicalApproach", "implementationMethodology", "supportAndSla"],
    ["securityCompliance", "relevantExperience", "caseStudies", "assumptions"],
]

SECTION_LABELS: dict[str, str] = {
    "executiveSummary": "Executive Summary",
    "understandingOfRequirements": "Understanding of Requirements",
    "proposedSolution": "Proposed Solution",
    "technicalApproach": "Technical Approach",
    "implementationMethodology": "Implementation Methodology",
    "supportAndSla": "Support & SLA",
    "securityCompliance": "Security & Compliance",
    "relevantExperience": "Relevant Experience",
    "caseStudies": "Case Studies",
    "assumptions": "Assumptions",
}

ProgressFn = Callable[..., None]


def _coerce_text(value: Any, max_len: int | None = None) -> str:
    """Normalize LLM output (string, list, or nested dict) into plain text."""
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    elif isinstance(value, list):
        parts = [_coerce_text(item) for item in value]
        text = "\n".join(part for part in parts if part)
    elif isinstance(value, dict):
        for key in ("text", "content", "body", "paragraph", "summary", "value"):
            if key in value:
                text = _coerce_text(value[key])
                break
        else:
            parts = [_coerce_text(item) for item in value.values()]
            text = "\n".join(part for part in parts if part)
    else:
        text = str(value)

    if max_len is not None:
        return text[:max_len]
    return text


def _proposal_model() -> str:
    return settings.proposal_model or settings.llm_fast_model


def _build_summary(responses: list[dict[str, Any]]) -> str:
    max_items = settings.proposal_max_responses
    max_chars = settings.proposal_response_chars
    lines: list[str] = []
    for resp in responses[:max_items]:
        req_id = resp.get("requirementId", "")
        text = (resp.get("response") or "")[:max_chars]
        status = resp.get("status", "")
        if text:
            lines.append(f"- {req_id} ({status}): {text}")
    return "\n".join(lines) or "- No reviewed responses available."


def _progress(
    on_progress: ProgressFn | None,
    percent: int,
    step: str,
    message: str,
    **extra: Any,
) -> None:
    if on_progress:
        on_progress(percent=percent, step=step, message=message, **extra)


async def _generate_batch(
    keys: list[str],
    summary: str,
    metadata: dict[str, Any],
) -> dict[str, str]:
    key_list = ", ".join(f'"{k}"' for k in keys)
    content = await ollama_provider.chat(
        messages=[
            {"role": "system", "content": PROPOSAL_SYSTEM},
            {
                "role": "user",
                "content": f"""Write these proposal sections from the reviewed RFP responses.

Customer: {metadata.get("customer", "Client")}
Industry: {metadata.get("industry", "General")}

Responses:
{summary}

Return JSON with ONLY these keys: {key_list}
Each value MUST be a plain string (2-3 concise paragraphs). Do not nest objects or arrays.

Example shape: {{{", ".join(f'"{k}": "paragraph text here"' for k in keys)}}}""",
            },
        ],
        model=_proposal_model(),
        format_json=True,
        disable_thinking=True,
        max_tokens=settings.proposal_max_tokens,
    )

    try:
        parsed = ollama_provider.parse_json_response(content)
        if isinstance(parsed, dict):
            return {k: _coerce_text(parsed.get(k, "")) for k in keys}
    except (ValueError, TypeError):
        pass

    return {k: "" for k in keys}


async def generate_proposal_content(
    metadata: dict[str, Any],
    requirements: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    compliance: dict[str, Any],
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    summary = _build_summary(responses)
    total_batches = len(PROPOSAL_BATCHES)
    done_batches = 0
    proposal: dict[str, Any] = {}
    sem = asyncio.Semaphore(max(1, settings.proposal_concurrency))

    async def run_batch(batch_idx: int, keys: list[str]) -> dict[str, str]:
        nonlocal done_batches
        labels = [SECTION_LABELS.get(k, k) for k in keys]
        async with sem:
            _progress(
                on_progress,
                5 + int((done_batches / total_batches) * 70),
                "writing",
                f"Writing: {', '.join(labels[:2])}{'…' if len(labels) > 2 else ''}",
                sectionDone=done_batches,
                sectionTotal=total_batches,
            )
            result = await _generate_batch(keys, summary, metadata)
            done_batches += 1
            _progress(
                on_progress,
                5 + int((done_batches / total_batches) * 70),
                "writing",
                f"Completed {done_batches}/{total_batches} section groups",
                sectionDone=done_batches,
                sectionTotal=total_batches,
            )
            return result

    batch_results = await asyncio.gather(
        *[run_batch(i, keys) for i, keys in enumerate(PROPOSAL_BATCHES)]
    )
    for batch in batch_results:
        proposal.update(batch)

    _progress(on_progress, 80, "render", "Building Word document…")
    proposal["complianceMatrix"] = compliance.get("complianceMatrix", [])
    proposal["customer"] = metadata.get("customer", "")
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
    doc.add_paragraph(f"Customer: {_coerce_text(proposal.get('customer', 'N/A'))}")

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
        text = _coerce_text(proposal.get(key, ""))
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
            cells[0].text = _coerce_text(row.get("requirementId", ""))
            cells[1].text = _coerce_text(row.get("requirement"), max_len=200)
            cells[2].text = _coerce_text(row.get("response"), max_len=300)
            cells[3].text = _coerce_text(row.get("status", ""))
            cells[4].text = "Yes" if row.get("reviewRequired") else "No"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path


def render_pptx(proposal: dict[str, Any], output_path: str, rfp_id: str) -> str:
    """Render proposal using the TTN PPTX template."""
    return render_pptx_from_template(proposal, output_path, rfp_id)


def find_libreoffice_command() -> str | None:
    for command in ("libreoffice", "soffice"):
        resolved = shutil.which(command)
        if resolved:
            return resolved

    mac_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if os.path.isfile(mac_path):
        return mac_path

    return None


def convert_to_pdf(docx_path: str, force: bool = False) -> str | None:
    """Convert DOCX to PDF using LibreOffice headless."""
    if not force and not settings.proposal_generate_pdf:
        return None

    libreoffice = find_libreoffice_command()
    if not libreoffice:
        return None

    pdf_path = docx_path.replace(".docx", ".pdf")
    try:
        subprocess.run(
            [
                libreoffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                os.path.dirname(docx_path),
                docx_path,
            ],
            check=True,
            capture_output=True,
            timeout=settings.proposal_pdf_timeout_seconds,
        )
        return pdf_path if os.path.exists(pdf_path) else None
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


async def build_proposal_files(
    rfp_id: str,
    metadata: dict[str, Any],
    requirements: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    compliance: dict[str, Any],
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    proposal = await generate_proposal_content(
        metadata, requirements, responses, compliance, on_progress=on_progress
    )

    docx_path = os.path.join(settings.proposal_dir, f"{rfp_id}_proposal.docx")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, partial(render_docx, proposal, docx_path, rfp_id)
    )

    _progress(on_progress, 88, "pptx", "Building PowerPoint deck…")
    pptx_path = os.path.join(settings.proposal_dir, f"{rfp_id}_proposal.pptx")
    await loop.run_in_executor(
        None, partial(render_pptx, proposal, pptx_path, rfp_id)
    )

    _progress(on_progress, 94, "pdf", "Converting to PDF (if available)…")
    pdf_path = await loop.run_in_executor(None, partial(convert_to_pdf, docx_path))

    _progress(on_progress, 100, "complete", "Proposal ready for download")
    return {
        "proposal": proposal,
        "docxPath": docx_path,
        "pptxPath": pptx_path,
        "pdfPath": pdf_path,
    }

from unittest.mock import AsyncMock, patch

import pytest

import tempfile
from pathlib import Path

from app.proposal.generator import (
    PROPOSAL_BATCHES,
    _build_summary,
    _coerce_text,
    generate_proposal_content,
    render_docx,
    render_pptx,
)


def test_coerce_text_handles_nested_dicts():
    assert _coerce_text({"content": "Hello"}) == "Hello"
    assert _coerce_text([{"text": "A"}, {"text": "B"}]) == "A\nB"
    assert _coerce_text({"nested": {"summary": "Done"}}) == "Done"


def test_render_docx_accepts_dict_section_values():
    with tempfile.TemporaryDirectory() as tmp:
        output = str(Path(tmp) / "proposal.docx")
        render_docx(
            {
                "customer": "Acme",
                "executiveSummary": {"content": "We propose Drupal Commerce."},
                "complianceMatrix": [
                    {
                        "requirementId": "REQ-001",
                        "requirement": "Search",
                        "response": {"text": "Supported via Search API"},
                        "status": "SUPPORTED",
                        "reviewRequired": False,
                    }
                ],
            },
            output,
            "rfp-123",
        )
        assert Path(output).exists()


def test_render_pptx_creates_deck_from_template():
    with tempfile.TemporaryDirectory() as tmp:
        output = str(Path(tmp) / "proposal.pptx")
        render_pptx(
            {
                "customer": "Acme",
                "executiveSummary": "We propose a scalable commerce platform.",
                "proposedSolution": "Drupal Commerce with Search API.",
            },
            output,
            "rfp-123",
        )
        assert Path(output).exists()
        assert Path(output).stat().st_size > 100_000


def test_build_summary_limits_size():
    responses = [
        {"requirementId": f"REQ-{i}", "response": "x" * 500, "status": "SUPPORTED"}
        for i in range(30)
    ]
    summary = _build_summary(responses)
    assert "REQ-0" in summary
    assert "REQ-29" not in summary
    assert len(summary.splitlines()) <= 25


@pytest.mark.asyncio
async def test_generate_proposal_content_parallel_batches():
    progress_calls: list[dict] = []

    def on_progress(**fields):
        progress_calls.append(fields)

    async def fake_batch(keys, summary, metadata):
        return {k: f"Section for {k}" for k in keys}

    with patch(
        "app.proposal.generator._generate_batch",
        new_callable=AsyncMock,
        side_effect=fake_batch,
    ) as batch_mock:
        result = await generate_proposal_content(
            {"customer": "Acme", "industry": "Tech"},
            [],
            [{"requirementId": "REQ-1", "response": "Yes", "status": "SUPPORTED"}],
            {"complianceMatrix": []},
            on_progress=on_progress,
        )

    assert batch_mock.await_count == len(PROPOSAL_BATCHES)
    assert result["executiveSummary"] == "Section for executiveSummary"
    assert result["assumptions"] == "Section for assumptions"
    assert any(call.get("step") == "writing" for call in progress_calls)

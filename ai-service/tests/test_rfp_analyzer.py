from unittest.mock import AsyncMock, patch

import pytest

from app.agents.rfp_analyzer import (
    _parse_analyzer_output,
    analyze_rfp,
    prepare_document_for_analysis,
)


def test_prepare_document_keeps_short_text_unchanged():
    text = "Short RFP with one requirement."
    assert prepare_document_for_analysis(text, max_chars=1000) == text


def test_prepare_document_prioritizes_requirement_sections():
    filler = "Lorem ipsum " * 500
    requirement = "The vendor shall provide Drupal Commerce with PCI-DSS compliance."
    text = f"{filler}\n\n{requirement}"
    prepared = prepare_document_for_analysis(text, max_chars=2000)
    assert "Drupal Commerce" in prepared
    assert len(prepared) <= 2000


def test_prepare_document_prioritizes_website_features():
    filler = "General company information. " * 500
    feature = "The platform feature lets customers compare products and save favorites."
    text = f"{filler}\n\n--- WEBSITE PAGE: https://example.com/features ---\n{feature}"

    prepared = prepare_document_for_analysis(text, max_chars=2000)

    assert "compare products" in prepared
    assert len(prepared) <= 2000


def test_prepare_website_analysis_represents_multiple_pages():
    pages = "\n\n".join(
        f"--- WEBSITE PAGE: https://example.com/page-{index} ---\n"
        f"Unique feature {index}\n" + ("Page details. " * 120)
        for index in range(1, 4)
    )
    text = f"=== WEBSITE SOURCE: https://example.com ===\n{pages}"

    prepared = prepare_document_for_analysis(text, max_chars=6000)

    assert "Unique feature 1" in prepared
    assert "Unique feature 2" in prepared
    assert "Unique feature 3" in prepared
    assert len(prepared) <= 6000


@pytest.mark.asyncio
async def test_website_only_requirements_are_marked_as_website_sources():
    with patch(
        "app.agents.rfp_analyzer.ollama_provider.chat",
        new_callable=AsyncMock,
        return_value=(
            '{"metadata": {}, "requirements": ['
            '{"id": "REQ-001", "description": "Account - User registration", '
            '"type": "Functional", "mandatory": true, '
            '"source_section": "https://example.com/register"}]}'
        ),
    ):
        result = await analyze_rfp(
            "=== WEBSITE SOURCE: https://example.com ===\n"
            "--- WEBSITE PAGE: https://example.com/register ---\nRegistration"
        )

    assert result["requirements"][0]["source_type"] == "website"


def test_parse_analyzer_output_recovers_complete_items_from_truncated_json():
    truncated = (
        '{"metadata": {}, "requirements": ['
        '{"id":"REQ-001","description":"Accounts - User login"},'
        '{"id":"REQ-002","description":"Search - Find races"},'
        '{"id":"REQ-003","description":"Incomplete'
    )

    result = _parse_analyzer_output(truncated)

    assert [item["id"] for item in result["requirements"]] == [
        "REQ-001",
        "REQ-002",
    ]

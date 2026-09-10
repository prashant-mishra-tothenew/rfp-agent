from unittest.mock import AsyncMock, patch

import pytest

from app.agents.response_agent import (
    _format_evidence,
    generate_response,
    generate_responses_batch,
)


def test_format_evidence_limits_size():
    evidence = [
        {"document_id": "doc-1", "content": "x" * 1000},
        {"document_id": "doc-2", "content": "y" * 1000},
        {"document_id": "doc-3", "content": "z" * 1000},
        {"document_id": "doc-4", "content": "extra"},
    ]
    text, refs = _format_evidence(evidence)
    assert "doc-4" not in text
    assert len(refs) == 3


@pytest.mark.asyncio
async def test_generate_response_skips_llm_without_evidence():
    with patch(
        "app.agents.response_agent.ollama_provider.chat",
        new_callable=AsyncMock,
    ) as chat_mock:
        result = await generate_response(
            {"id": "REQ-001", "description": "Test"},
            [],
        )
    chat_mock.assert_not_called()
    assert result["status"] == "HUMAN_VERIFICATION_REQUIRED"


@pytest.mark.asyncio
async def test_generate_responses_batch_parses_multiple():
    items = [
        (
            {"id": "REQ-001", "description": "Drupal Commerce", "type": "Technical"},
            [{"document_id": "doc-1", "content": "We use Drupal Commerce"}],
        ),
        (
            {"id": "REQ-002", "description": "Search API", "type": "Technical"},
            [{"document_id": "doc-2", "content": "Search API faceted"}],
        ),
    ]

    with patch(
        "app.agents.response_agent.ollama_provider.chat",
        new_callable=AsyncMock,
        return_value='{"responses": [{"requirementId": "REQ-001", "response": "Yes", "status": "SUPPORTED", "confidence": 0.9, "evidence": ["doc-1"], "reviewRequired": false, "gaps": []}, {"requirementId": "REQ-002", "response": "Yes", "status": "SUPPORTED", "confidence": 0.8, "evidence": ["doc-2"], "reviewRequired": false, "gaps": []}]}',
    ) as chat_mock:
        results = await generate_responses_batch(items)

    assert chat_mock.await_count == 1
    assert len(results) == 2
    assert results[0]["requirementId"] == "REQ-001"

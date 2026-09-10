from unittest.mock import AsyncMock, patch

import pytest

from app.agents.knowledge_agent import retrieve_knowledge


@pytest.mark.asyncio
async def test_retrieve_skips_expansion_when_direct_search_is_strong():
    strong_hit = {"id": "1", "score": 0.8, "content": "Drupal Commerce checkout"}

    with patch(
        "app.agents.knowledge_agent.milvus_store.search",
        new_callable=AsyncMock,
        return_value=[strong_hit],
    ) as search_mock, patch(
        "app.agents.knowledge_agent.ollama_provider.chat",
        new_callable=AsyncMock,
    ) as chat_mock:
        hits = await retrieve_knowledge(
            {"description": "Drupal Commerce checkout workflows"},
            filters={"approved": True},
        )

    assert hits == [strong_hit]
    assert search_mock.await_count == 1
    chat_mock.assert_not_called()


@pytest.mark.asyncio
async def test_retrieve_expands_when_direct_search_is_weak():
    weak_hit = {"id": "1", "score": 0.2, "content": "generic portal"}
    strong_hit = {"id": "2", "score": 0.9, "content": "Drupal Search API"}

    async def search_side_effect(query, top_k=5, filters=None):
        if "Drupal Search API" in query:
            return [strong_hit]
        return [weak_hit]

    with patch(
        "app.agents.knowledge_agent.milvus_store.search",
        side_effect=search_side_effect,
    ), patch(
        "app.agents.knowledge_agent.ollama_provider.chat",
        new_callable=AsyncMock,
        return_value='{"queries": ["Drupal Search API faceted filtering"]}',
    ), patch(
        "app.agents.knowledge_agent.ollama_provider.parse_json_response",
        return_value={"queries": ["Drupal Search API faceted filtering"]},
    ):
        hits = await retrieve_knowledge(
            {"description": "Support faceted product search"},
            filters={"approved": True},
        )

    assert hits[0]["id"] == "2"

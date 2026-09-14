from unittest.mock import AsyncMock, patch

import pytest

from app.agents.orchestrator import knowledge_node


@pytest.mark.asyncio
async def test_website_features_skip_knowledge_retrieval():
    state = {
        "requirements": [
            {
                "id": "REQ-001",
                "description": "Accounts - User registration",
                "source_type": "website",
                "source_section": "https://example.com/register",
            }
        ],
        "filters": {"approved": True},
    }

    with patch(
        "app.agents.orchestrator.retrieve_knowledge",
        new_callable=AsyncMock,
    ) as retrieve_mock:
        result = await knowledge_node(state)

    retrieve_mock.assert_not_awaited()
    assert result["evidence_map"] == {"REQ-001": []}

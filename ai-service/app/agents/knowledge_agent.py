from typing import Any

from app.config import settings
from app.providers.ollama_provider import ollama_provider
from app.rag.milvus_store import milvus_store

KNOWLEDGE_SYSTEM = """You are a Knowledge Agent. Expand search queries to find relevant historical RFP responses and company evidence.
Return a JSON object with an array of 2-3 optimized search queries."""


async def retrieve_knowledge(
    requirement: dict[str, Any],
    filters: dict[str, Any] | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    req_text = requirement.get("description") or requirement.get("text", "")

    # Query expansion with fast model
    try:
        expanded = await ollama_provider.chat(
            messages=[
                {"role": "system", "content": KNOWLEDGE_SYSTEM},
                {
                    "role": "user",
                    "content": f'Requirement: "{req_text}"\nReturn JSON: {{"queries": ["...", "..."]}}',
                },
            ],
            model=settings.llm_fast_model,
            format_json=True,
        )
        parsed = ollama_provider.parse_json_response(expanded)
        queries = parsed.get("queries", [req_text])
    except (ValueError, TypeError):
        queries = [req_text]

    all_hits: dict[str, dict[str, Any]] = {}
    for query in queries[:3]:
        hits = await milvus_store.search(query, top_k=top_k, filters=filters)
        for hit in hits:
            hit_id = str(hit.get("id", hit.get("content", "")[:50]))
            if hit_id not in all_hits or hit["score"] > all_hits[hit_id]["score"]:
                all_hits[hit_id] = hit

    return sorted(all_hits.values(), key=lambda h: h["score"], reverse=True)[:top_k]

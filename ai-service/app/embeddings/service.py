from app.providers.ollama_provider import ollama_provider

_cache: dict[str, list[float]] = {}


def clear_embedding_cache() -> None:
    _cache.clear()


async def embed_text(text: str) -> list[float]:
    key = text.strip()
    if key in _cache:
        return _cache[key]
    vector = await ollama_provider.embed(text)
    _cache[key] = vector
    return vector


async def embed_texts(texts: list[str]) -> list[list[float]]:
    return [await embed_text(t) for t in texts]

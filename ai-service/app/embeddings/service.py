from app.providers.ollama_provider import ollama_provider


async def embed_text(text: str) -> list[float]:
    return await ollama_provider.embed(text)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    return [await embed_text(t) for t in texts]

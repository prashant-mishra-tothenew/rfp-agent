import json
import re
from typing import Any

import httpx

from app.config import settings


class OllamaProvider:
    """Encapsulates Ollama HTTP API behind a provider interface."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
        format_json: bool = False,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model or settings.llm_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if format_json:
            payload["format"] = "json"

        timeout = httpx.Timeout(settings.ollama_timeout_seconds, connect=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat", json=payload
            )
            response.raise_for_status()
            return response.json()["message"]["content"]

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model or settings.embedding_model, "prompt": text},
            )
            response.raise_for_status()
            return response.json()["embedding"]

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    @staticmethod
    def parse_json_response(content: str) -> dict | list:
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
        return json.loads(content)


ollama_provider = OllamaProvider()

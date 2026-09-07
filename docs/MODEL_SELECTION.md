# LLM Model Selection for RFP Agent

## Selected Models (Ollama)

| Role | Model | Rationale |
|------|-------|-----------|
| **Primary chat / solution drafting** | `qwen3:32b` | Best open-weight balance for multi-step agentic work, structured extraction, and evidence-backed response generation on a single 24GB+ GPU |
| **Fast classification / routing** | `qwen3:8b` | Lower latency for requirement classification and compliance checks |
| **Embeddings** | `nomic-embed-text` | Strong semantic retrieval, widely used with Milvus + Ollama |
| **Cloud fallback (optional)** | `glm-5.2:cloud` | MIT-licensed frontier model via Ollama Cloud for teams without local GPU |

## Hardware Guidance

| GPU RAM | Recommended chat model |
|---------|------------------------|
| 8–16 GB | `qwen3:8b` |
| 24 GB | `qwen3:14b` or `qwen3:32b` (Q4) |
| 48 GB+ | `qwen3:32b` (Q8) or `glm-5.2` local |
| No GPU | `glm-5.2:cloud` or `deepseek-v4-flash:cloud` |

## Multi-Agent Orchestration

LangGraph orchestrates three specialized agents:

1. **RFP Analyzer** — document parsing, requirement extraction (`qwen3:32b`)
2. **Knowledge Agent** — hybrid RAG retrieval from Milvus (`qwen3:8b` for query expansion)
3. **Response Agent** — evidence-backed draft responses (`qwen3:32b`)

A deterministic **Compliance Checker** runs after generation (no LLM).

## Environment Variables

```bash
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:32b
LLM_FAST_MODEL=qwen3:8b
EMBEDDING_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://ollama:11434
```

## Benchmarking

Swap models via env vars without code changes. Compare on your RFP dataset using the `/ai/benchmark` endpoint.

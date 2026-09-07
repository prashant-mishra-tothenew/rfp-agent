# RFP Response Accelerator

AI-powered RFP response assistant that reuses institutional knowledge safely. Built for hackathon/showcase with **multi-agent LangGraph orchestration** and **local Ollama LLMs**.

## Architecture

```
Next.js UI  →  Node.js API  →  Python FastAPI (LangGraph)
                                    ├── RFP Analyzer Agent
                                    ├── Knowledge Agent (Milvus RAG)
                                    ├── Response Agent
                                    └── Compliance Checker
                                          ↓
                                       Ollama (qwen3:32b)
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 24GB+ GPU recommended for `qwen3:32b` (or use `qwen3:8b` for lighter hardware)

### 1. Start all services

```bash
cp .env.example .env
docker compose up --build
```

On first run, `ollama-init` pulls:
- `qwen3:32b` — primary chat/solution model
- `qwen3:8b` — fast classification/routing
- `nomic-embed-text` — embeddings for Milvus

### 2. Ingest historical knowledge

Place historical RFP PDFs/DOCX in `ingestion/historical-rfps/`, then:

```bash
docker compose exec python-ai python /app/ingestion/scripts/ingest.py
```

Or locally:

```bash
cd ai-service && pip install -r requirements.txt
python ../ingestion/scripts/ingest.py --dir ../ingestion/historical-rfps
```

### 3. Open the app

- **UI**: http://localhost:3000
- **API**: http://localhost:3001
- **AI Service**: http://localhost:8000/docs

## Workflow

1. Upload a new RFP (PDF/DOCX)
2. Click **Generate Draft Responses** — runs the LangGraph pipeline:
   - **Analyzer** → extract requirements
   - **Knowledge** → hybrid RAG search in Milvus
   - **Response** → evidence-backed draft answers
   - **Compliance** → gap analysis matrix
3. Review, edit, accept/reject responses
4. Generate DOCX/PDF proposal

## Model Configuration

See [docs/MODEL_SELECTION.md](docs/MODEL_SELECTION.md) for details.

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_MODEL` | `qwen3:32b` | Solution drafting, requirement extraction |
| `LLM_FAST_MODEL` | `qwen3:8b` | Query expansion, classification |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Vector search |

For cloud-only setups, set `LLM_MODEL=glm-5.2:cloud`.

## Project Structure

```
rfp_agent/
├── frontend/nextjs-app/     # Next.js UI
├── api/nodejs/              # Fastify API + SQLite
├── ai-service/              # FastAPI + LangGraph agents
├── ingestion/               # Historical data + scripts
├── templates/               # Proposal DOCX template
├── docs/                    # Requirements, design, integration
└── docker-compose.yml
```

## Development (without Docker)

```bash
# Terminal 1: Ollama
ollama pull qwen3:32b qwen3:8b nomic-embed-text
ollama serve

# Terminal 2: Milvus (or use docker compose up milvus etcd minio)
docker compose up milvus etcd minio

# Terminal 3: AI Service
cd ai-service && pip install -r requirements.txt
uvicorn app.api.main:app --reload --port 8000

# Terminal 4: Node API
cd api/nodejs && npm install && npm run dev

# Terminal 5: Frontend
cd frontend/nextjs-app && npm install && npm run dev
```

## Tests

```bash
cd ai-service && pip install -r requirements.txt pytest
pytest tests/
```

## Documentation

- **[Mac Getting Started](docs/MAC_GETTING_STARTED.md)** — setup on Mac for any developer (PHP, Java, etc.)
- [End-to-End Journey](docs/END_TO_END_JOURNEY.md)
- [Requirements](docs/RFP_Agent_Requirements.md)
- [Design](docs/RFP_Agent_Design.md)
- [Integration](docs/RFP_Agent_Integration.md)
- [Model Selection](docs/MODEL_SELECTION.md)

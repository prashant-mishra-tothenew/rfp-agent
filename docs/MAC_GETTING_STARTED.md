# Mac Getting Started Guide

**For developers from any background** (PHP, Java, .NET, Ruby, etc.) who want to run the RFP Agent on a Mac.

**Also read:** [End-to-End Journey](END_TO_END_JOURNEY.md) for how to use the app after it is running.

---

## What you are starting

This project has **4 moving parts** (think of them like separate services in a microservice setup):

| Part | Technology | Port | What it does |
|------|------------|------|--------------|
| Frontend | Next.js (React) | 3000 | Web UI in the browser |
| API | Node.js (Fastify) | 3001 | REST API, file uploads, SQLite DB |
| AI Service | Python (FastAPI) | 8000 | LLM agents, RAG, document parsing |
| Milvus | Docker | 19530 | Vector database for knowledge search |
| Ollama | Local app | 11434 | Runs the AI models on your Mac |

**PHP analogy:** Next.js = your frontend, Node API = your Laravel/Symfony controllers, Python AI = a separate microservice you call over HTTP, Milvus = like Elasticsearch for AI embeddings.

---

## Choose your setup path

| Path | Best for | Difficulty |
|------|----------|------------|
| **[A] Hybrid local (recommended on Mac)** | Daily development, faster iteration | Medium |
| **[B] Full Docker** | One-command start, closer to production | Easy start, slower builds |

Most Mac developers use **Path A** because Python 3.14 (default on newer Macs) is not compatible with all AI libraries yet — we use Python 3.12 in a virtual environment instead.

---

## Prerequisites (install once)

Open **Terminal** (`Applications → Utilities → Terminal`).

### 1. Install Homebrew (if you don't have it)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install required tools

```bash
brew install node python@3.12 docker ollama
```

| Tool | Why you need it |
|------|-----------------|
| **node** | Runs the API and frontend (`npm`) |
| **python@3.12** | Runs the AI service (do not use 3.14) |
| **docker** | Runs Milvus vector database |
| **ollama** | Runs local LLM models |

### 3. Start Docker Desktop

```bash
open -a Docker
```

Wait until the Docker whale icon in the menu bar shows **Running**.

### 4. Start Ollama and download models

```bash
ollama serve          # or just open the Ollama app from Applications
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

> **Hardware note:** `qwen3:8b` works on most Macs (8GB+ RAM). For better quality on a 24GB+ machine, also pull `qwen3:32b` and set `LLM_MODEL=qwen3:32b` in `.env`.

### 5. Clone / open the project

```bash
cd /path/to/rfp_agent
cp .env.example .env
```

---

## Path A — Hybrid local setup (recommended)

You will open **5 terminal tabs**. Keep each one running.

### Terminal 1 — Milvus (Docker)

```bash
cd /path/to/rfp_agent
docker compose up -d etcd minio milvus
```

Wait ~60 seconds, then check:

```bash
docker compose ps
# milvus should show "healthy"
```

### Terminal 2 — AI Service (Python)

```bash
cd /path/to/rfp_agent/ai-service

# Create virtual environment (only first time)
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the service
export OLLAMA_BASE_URL=http://localhost:11434
export LLM_MODEL=qwen3:8b
export LLM_FAST_MODEL=qwen3:8b
export EMBEDDING_MODEL=nomic-embed-text
export MILVUS_HOST=localhost
export MILVUS_PORT=19530
export UPLOAD_DIR=/path/to/rfp_agent/data/uploads
export PROPOSAL_DIR=/path/to/rfp_agent/data/proposals
export PYTHONPATH=/path/to/rfp_agent/ai-service

uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

Replace `/path/to/rfp_agent` with your actual project path.

### Terminal 3 — Node API

```bash
cd /path/to/rfp_agent/api/nodejs
npm install          # only first time

export DATABASE_PATH=/path/to/rfp_agent/data/rfp.db
export UPLOAD_DIR=/path/to/rfp_agent/data/uploads
export PROPOSAL_DIR=/path/to/rfp_agent/data/proposals
export AI_SERVICE_URL=http://localhost:8000

npm run dev
```

### Terminal 4 — Frontend

```bash
cd /path/to/rfp_agent/frontend/nextjs-app
npm install          # only first time

export NEXT_PUBLIC_API_URL=http://localhost:3001
npm run dev
```

### Terminal 5 — Verify (optional)

```bash
curl http://localhost:8000/health
curl http://localhost:3001/health
open http://localhost:3000
```

---

## Path B — Full Docker setup

```bash
cd /path/to/rfp_agent
cp .env.example .env
docker compose up --build
```

**Requirements:**
- Docker Desktop must be running
- Ollama app running on the Mac (Docker uses `host.docker.internal:11434` for models)
- First build can take 10–20 minutes (downloads images + models)

**Open:** http://localhost:3000

---

## Verify everything works

| Check | Command or URL | Expected |
|-------|----------------|----------|
| Frontend | http://localhost:3000 | Upload page loads |
| API | http://localhost:3001/health | `{"status":"ok"}` |
| AI Service | http://localhost:8000/health | `"ollama": true` |
| Ollama | `ollama list` | Shows `qwen3:8b`, `nomic-embed-text` |
| Milvus | `docker compose ps` | milvus = healthy |

---

## First use (5 minutes)

1. **Load knowledge** → http://localhost:3000/knowledge  
   Upload a historical PDF/DOCX, set status to **Approved**, click **Ingest**.

2. **Analyze RFP** → http://localhost:3000  
   Upload a new RFP, click **Generate Draft Responses**.

3. **Review** → Accept or edit responses on the analysis page.

4. **Export** → Click **Generate Proposal** → Download DOCX.

Full walkthrough: [END_TO_END_JOURNEY.md](END_TO_END_JOURNEY.md)

---

## Stop all services

```bash
# Stop local servers (Ctrl+C in each terminal tab)

# Stop Docker (Milvus)
cd /path/to/rfp_agent
docker compose down

# Optional: stop Ollama
pkill ollama
```

---

## Troubleshooting (Mac)

### `Docker daemon is not running`

```bash
open -a Docker
# Wait 30 seconds, then retry
```

### `ModuleNotFoundError: No module named 'app'` (ingest script)

Run ingest from project root with the AI venv active:

```bash
cd ai-service && source .venv/bin/activate
python ../ingestion/scripts/ingest.py
```

Or use the **Knowledge Base UI** at http://localhost:3000/knowledge instead.

### Python `externally-managed-environment` error

Do **not** install packages globally. Always use the venv:

```bash
cd ai-service
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### `pydantic-core` build fails on Python 3.14

Use Python 3.12:

```bash
brew install python@3.12
/opt/homebrew/bin/python3.12 -m venv .venv
```

### Port already in use (`EADDRINUSE`)

```bash
lsof -ti:3000 | xargs kill
lsof -ti:3001 | xargs kill
lsof -ti:8000 | xargs kill
```

### AI service health shows `"ollama": false`

```bash
ollama serve
ollama pull qwen3:8b
```

### No evidence in generated responses

Ingest historical documents first via http://localhost:3000/knowledge.

### Docker build fails on `libreoffice`

Use **Path A (hybrid local)** instead of full Docker for the AI service.

---

## Project folders (quick map)

```
rfp_agent/
├── frontend/nextjs-app/   ← React UI (like your PHP views + JS)
├── api/nodejs/            ← REST API (like Laravel routes/controllers)
├── ai-service/            ← Python AI microservice
├── ingestion/             ← Scripts + sample historical files
├── data/                  ← Uploads, proposals, SQLite DB (auto-created)
├── docs/                  ← All documentation
└── docker-compose.yml     ← Infrastructure definition
```

---

## Environment variables cheat sheet

Copy `.env.example` to `.env`. Key settings:

```bash
LLM_MODEL=qwen3:8b              # Main AI model
EMBEDDING_MODEL=nomic-embed-text  # For Milvus search
OLLAMA_BASE_URL=http://localhost:11434
AI_SERVICE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:3001
```

---

## Other documentation

| Doc | Purpose |
|-----|---------|
| [END_TO_END_JOURNEY.md](END_TO_END_JOURNEY.md) | How to use the app step by step |
| [MODEL_SELECTION.md](MODEL_SELECTION.md) | Which Ollama model to pick |
| [RFP_Agent_Integration.md](RFP_Agent_Integration.md) | API endpoints for integrators |
| [RFP_Agent_Design.md](RFP_Agent_Design.md) | Architecture deep dive |

---

## Quick reference card

```bash
# START (hybrid)
docker compose up -d etcd minio milvus
cd ai-service && source .venv/bin/activate && uvicorn app.api.main:app --port 8000
cd api/nodejs && npm run dev
cd frontend/nextjs-app && npm run dev

# OPEN
open http://localhost:3000

# STOP
docker compose down
# Ctrl+C in each terminal
```

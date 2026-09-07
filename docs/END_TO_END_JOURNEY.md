# End-to-End Journey

A simple walkthrough of the RFP Response Accelerator — from setup to a finished proposal draft.

**Audience:** Sales, proposal managers, solution architects (no AI expertise required).

**Time:** ~30 minutes for first run (including service startup).

---

## Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  1. Setup       │ ──► │  2. Load        │ ──► │  3. Analyze     │
│  Start services │     │  Knowledge Base │     │  New RFP        │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
┌─────────────────┐     ┌─────────────────┐              │
│  6. Export      │ ◄── │  5. Review      │ ◄────────────┘
│  DOCX / PDF     │     │  & Approve      │     4. Generate drafts
└─────────────────┘     └─────────────────┘
```

---

## Step 0 — Start the application

### Option A: Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

### Option B: Local development

```bash
# Terminal 1 — Milvus
docker compose up -d etcd minio milvus

# Terminal 2 — Ollama (if not already running)
ollama serve
ollama pull qwen3:8b nomic-embed-text

# Terminal 3 — AI service
cd ai-service && source .venv/bin/activate
uvicorn app.api.main:app --port 8000

# Terminal 4 — Node API
cd api/nodejs && npm run dev

# Terminal 5 — Frontend
cd frontend/nextjs-app && npm run dev
```

### Verify

| Service   | URL                        | Check              |
|-----------|----------------------------|--------------------|
| Frontend  | http://localhost:3000      | Home page loads    |
| API       | http://localhost:3001/health | `{"status":"ok"}` |
| AI Service| http://localhost:8000/health | `ollama: true`    |

> **Mac developers:** See [MAC_GETTING_STARTED.md](MAC_GETTING_STARTED.md) for full install steps, troubleshooting, and PHP-friendly explanations.

---

## Step 1 — Load historical knowledge

Before analyzing a new RFP, ingest approved company content so the AI can retrieve real evidence.

**Go to:** http://localhost:3000/knowledge

1. Click **Knowledge Base** in the navigation.
2. Select one or more files (PDF or DOCX):
   - Past RFP responses
   - Proposal documents
   - Case studies
   - Technical / security / capability documents
3. Fill in metadata:
   - **Document type** — e.g. Historical RFP, Case Study
   - **Industry** — e.g. Banking, Healthcare
   - **Year** — e.g. 2025
   - **Approval status** — use **Approved** for content safe to use in auto-generated responses
4. Click **Ingest Documents**.
5. Confirm the file appears in the **Ingested Documents** table with a chunk count.

> **Tip:** Only **Approved** content is used during automatic response generation. Draft or expired documents should be tagged accordingly.

### Alternative: CLI ingestion

```bash
# Place files in ingestion/historical-rfps/
python ingestion/scripts/ingest.py --dir ./ingestion/historical-rfps --industry Technology
```

---

## Step 2 — Upload a new RFP

**Go to:** http://localhost:3000

1. Click **New RFP** in the navigation.
2. Select the customer's RFP file (PDF or DOCX).
3. Enter **Customer** name.
4. Select **Industry**.
5. Click **Analyze RFP**.

You are taken to the RFP analysis page for that upload.

---

## Step 3 — Generate draft responses

On the RFP analysis page:

1. Click **Generate Draft Responses**.

This runs the multi-agent pipeline:

| Agent              | What it does                                      |
|--------------------|---------------------------------------------------|
| RFP Analyzer       | Extracts and classifies requirements              |
| Knowledge Agent    | Searches Milvus for matching historical evidence  |
| Response Agent     | Writes evidence-backed draft answers              |
| Compliance Checker | Flags gaps and builds a coverage summary          |

2. Wait for processing to complete (progress shown on screen).
3. Review the summary cards:
   - Total requirements
   - Supported / Partial / Missing
   - Coverage %

---

## Step 4 — Review each requirement

For every requirement you will see:

- **Requirement text** and type (Technical, Security, Commercial, etc.)
- **Generated response** — draft answer adapted to this RFP
- **Evidence** — source documents used (clickable references)
- **Status** — Supported, Partially Supported, Not Supported, or Human Verification Required
- **Confidence** — supporting signal (not a guarantee)

### Actions per requirement

| Action   | When to use                                      |
|----------|--------------------------------------------------|
| Accept   | Response is accurate and ready                   |
| Edit     | Response needs minor changes                     |
| Reject   | Response is wrong; needs SME rewrite             |

> **Rule:** If status is **Human Verification Required**, an SME must validate before the proposal is finalized. The system will not invent certifications, SLAs, or customer references.

---

## Step 5 — Generate the proposal

1. After reviewing responses, click **Generate Proposal**.
2. The system assembles:
   - Executive summary
   - Understanding of requirements
   - Proposed solution & technical approach
   - Implementation, support, security sections
   - Compliance matrix
3. Download outputs:
   - **Download DOCX** — editable Word document
   - **Download PDF** — shareable PDF (requires LibreOffice in the AI service container)

---

## Complete journey checklist

Use this checklist for a demo or acceptance test:

- [ ] Services running (frontend, API, AI, Milvus, Ollama)
- [ ] At least one historical document ingested via Knowledge Base
- [ ] New RFP uploaded (PDF or DOCX)
- [ ] Requirements extracted (visible on analysis page)
- [ ] Draft responses generated with evidence links
- [ ] At least one gap or “human verification” item identified
- [ ] User reviewed and accepted/edited a response
- [ ] Proposal DOCX generated and downloaded

---

## What the user sees vs what runs behind the scenes

```
YOU (browser)                SYSTEM
─────────────                ──────
Upload RFP          ──►      File saved → text extracted
Click Generate      ──►      LangGraph agents run
See requirements    ◄──      LLM structures RFP content
See evidence        ◄──      Milvus returns matching chunks
See draft answers   ◄──      LLM writes using evidence only
Review & edit       ──►      Saved to SQLite
Generate proposal   ──►      Structured JSON → DOCX → PDF
Download            ◄──      File served from API
```

---

## Common scenarios

### No evidence found for a requirement

**Cause:** No matching content in the knowledge base.  
**Action:** Ingest relevant historical documents on the Knowledge Base page, then regenerate.

### “Human Verification Required” on many items

**Cause:** Normal for a thin knowledge base or highly specific RFP.  
**Action:** SME reviews those items manually; do not accept unverified claims.

### Upload or ingest fails

**Check:**
1. API running at http://localhost:3001/health
2. AI service running at http://localhost:8000/health
3. Ollama running (`ollama list` shows `qwen3:8b` and `nomic-embed-text`)
4. Milvus running (`docker compose ps` shows milvus healthy)

### Slow response generation

**Cause:** LLM inference on large RFPs takes time.  
**Action:** Use `qwen3:8b` for faster local runs; use `glm-5.2:cloud` for higher quality.

---

## Roles in the journey

| Role              | Steps they own                          |
|-------------------|-----------------------------------------|
| Project team      | Step 1 — ingest historical knowledge    |
| Proposal manager  | Steps 2–5 — upload, review, export      |
| SME               | Step 4 — verify technical/legal claims  |
| Admin             | Step 0 — service setup and model config |

---

## Related documentation

- [Requirements](RFP_Agent_Requirements.md) — full functional spec
- [Design](RFP_Agent_Design.md) — architecture and agent design
- [Integration](RFP_Agent_Integration.md) — API and service integration
- [Model Selection](MODEL_SELECTION.md) — Ollama model choices

---

## One-line summary

> **Load approved company knowledge → upload a new RFP → let AI draft evidence-backed responses → human review → export a professional proposal.**

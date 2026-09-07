# AI-Powered RFP Response Accelerator --- Integration Design

## 1. Integration Overview

The application uses a two-language architecture:

-   Node.js/TypeScript for the application, API, and UI-facing
    orchestration
-   Python for AI, RAG, document processing, and agent execution

The architecture is intentionally lightweight for a hackathon and can
run through Docker Compose.

``` text
                 +----------------+
                 | Next.js / UI   |
                 +-------+--------+
                         |
                         v
                 +----------------+
                 | Node.js API    |
                 | TypeScript     |
                 +-------+--------+
                         |
                    HTTP/REST
                         |
                         v
                 +----------------+
                 | Python FastAPI |
                 | AI Service     |
                 +---+---+---+----+
                     |   |   |
                     |   |   +----------------+
                     |   |                    |
                     v   v                    v
                 Ollama Milvus          Document Tools
```

## 2. Node.js ↔ Python Integration

Recommended protocol:

-   REST/JSON for the hackathon
-   HTTP between Node.js and FastAPI

Example:

``` text
POST /api/rfp/analyze
POST /api/rfp/requirements
POST /api/rfp/generate
POST /api/rfp/compliance
POST /api/proposal/generate
```

The Node.js layer should remain responsible for application-level
workflow, while Python owns AI processing.

## 3. Suggested API Flow

### Upload

``` http
POST /api/rfps
Content-Type: multipart/form-data
```

Node.js receives the file and creates an RFP job.

### Analyze

``` http
POST /api/rfps/{rfpId}/analyze
```

Node.js invokes Python:

``` http
POST /ai/rfp/analyze
```

Python:

1.  Parses the document.
2.  Extracts text.
3.  Calls the LLM.
4.  Produces structured requirements.
5.  Returns JSON.

### Search Knowledge

``` http
POST /ai/knowledge/search
```

Example request:

``` json
{
  "query": "Solution must support Kubernetes",
  "filters": {
    "approved": true
  },
  "topK": 5
}
```

Python performs:

1.  Embedding generation
2.  Milvus search
3.  Optional sparse/keyword search
4.  Reranking
5.  Evidence formatting

### Generate Response

``` http
POST /ai/rfp/generate-response
```

Example:

``` json
{
  "requirement": {
    "id": "REQ-023",
    "text": "Solution must support Kubernetes"
  },
  "evidence": [
    {
      "source": "RFP-2025-017",
      "content": "..."
    }
  ]
}
```

Response:

``` json
{
  "requirementId": "REQ-023",
  "response": "Our proposed solution supports...",
  "status": "SUPPORTED",
  "evidence": [
    "RFP-2025-017",
    "Architecture-v3.2"
  ],
  "reviewRequired": false
}
```

## 4. Ollama Integration

Ollama runs locally and exposes an HTTP API.

Python should encapsulate the Ollama client behind an AI provider
interface.

``` text
AIProvider
   |
   +-- OllamaProvider
   |
   +-- FutureOpenAIProvider
   |
   +-- FutureBedrockProvider
```

This prevents the rest of the application from becoming dependent on a
single model provider.

## 5. Model Configuration

Use environment variables/configuration rather than hard-coding the
model.

Example:

``` text
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:32b
LLM_FAST_MODEL=qwen3:8b
EMBEDDING_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://ollama:11434
```

See `docs/MODEL_SELECTION.md` for hardware guidance and cloud fallback options.

The final model should be selected through benchmarking rather than
assuming that the largest model is always the best.

## 6. Milvus Integration

Milvus is the central retrieval layer for historical RFP knowledge.

Recommended logical collection:

``` text
rfp_knowledge
```

Suggested fields:

``` text
id
document_id
document_type
section
content
industry
geography
technology
year
approval_status
confidentiality
source_page
dense_vector
sparse_vector
```

## 7. Ingestion Pipeline

``` text
Historical PDF/DOCX
        |
        v
Python Document Parser
        |
        v
Text + Structure
        |
        v
Semantic Chunking
        |
        v
Metadata Enrichment
        |
        +------------------+
        |                  |
        v                  v
Embedding Model      Sparse Index
        |                  |
        +--------+---------+
                 |
                 v
               Milvus
```

The ingestion pipeline should be run before the live RFP demonstration.

## 8. Historical RFP Reuse

A new requirement triggers retrieval:

``` text
New Requirement
      |
      v
Embedding
      |
      +---- Dense Milvus Search
      |
      +---- Keyword/Sparse Search
      |
      v
Candidate Results
      |
      v
Metadata Filtering
      |
      v
Reranking
      |
      v
Top Evidence
      |
      v
Ollama
```

Metadata filters should prioritize:

-   approved content
-   current content
-   relevant industry
-   relevant technology
-   relevant geography
-   appropriate document type

## 9. Document Processing Integration

### PDF

Use PyMuPDF for:

-   text extraction
-   page extraction
-   metadata
-   source page references

For scanned PDFs, OCR can be added later.

### DOCX

Use python-docx for:

-   paragraphs
-   headings
-   tables
-   document generation

### PDF Output

The recommended showcase flow is:

``` text
Approved Proposal
       |
       v
python-docx
       |
       v
Proposal.docx
       |
       v
LibreOffice headless
       |
       v
Proposal.pdf
```

## 10. Proposal Template Integration

Keep company formatting separate from AI logic.

``` text
AI Output
   |
   v
Structured Proposal JSON
   |
   v
Template Renderer
   |
   v
Company Proposal DOCX
```

Example structured output:

``` json
{
  "executiveSummary": "...",
  "solution": "...",
  "implementation": "...",
  "security": "...",
  "support": "...",
  "caseStudies": [],
  "complianceMatrix": []
}
```

## 11. Frontend Integration

The UI communicates only with Node.js.

``` text
Browser
  |
  v
Next.js
  |
  v
Node.js API
  |
  v
Python AI Service
```

The browser should not directly communicate with Ollama or Milvus.

## 12. Suggested API Endpoints

``` text
POST   /api/rfps
GET    /api/rfps/:id
POST   /api/rfps/:id/analyze
GET    /api/rfps/:id/requirements

POST   /api/requirements/:id/search
POST   /api/requirements/:id/generate
POST   /api/rfps/:id/compliance

POST   /api/rfps/:id/review
POST   /api/rfps/:id/proposal

GET    /api/rfps/:id/download/docx
GET    /api/rfps/:id/download/pdf
```

## 13. Docker Compose

The showcase can run as:

``` text
docker compose up
```

Services:

``` text
frontend
node-api
python-ai
ollama
milvus
etcd
minio
```

Note: Milvus itself may use supporting services depending on the
selected Milvus deployment mode. These are infrastructure dependencies
of Milvus and are separate from the application's production storage
architecture.

## 14. Integration Sequence

### Historical Data Setup

``` text
Documents
   |
   v
Python Ingestion
   |
   v
Milvus
```

### New RFP

``` text
Employee
   |
   v
Next.js
   |
   v
Node.js
   |
   v
Python
   |
   +--> Parse RFP
   |
   +--> Extract Requirements
   |
   +--> Search Milvus
   |
   +--> Call Ollama
   |
   +--> Compliance Check
   |
   v
Node.js
   |
   v
Next.js
```

### Final Proposal

``` text
Reviewed Responses
       |
       v
Python Proposal Generator
       |
       v
DOCX
       |
       v
LibreOffice
       |
       v
PDF
```

## 15. Error Handling

The system should gracefully handle:

-   Unsupported document
-   Empty document
-   Parsing failure
-   No retrieval results
-   Ollama unavailable
-   Milvus unavailable
-   Model timeout
-   Insufficient evidence
-   DOCX generation failure
-   PDF conversion failure

When no evidence is found, the agent must not fabricate a response.

Example:

``` text
No reliable company evidence found.

Status:
HUMAN VERIFICATION REQUIRED
```

## 16. Future Integration Options

After the hackathon, the architecture can integrate with:

-   Microsoft SharePoint
-   Microsoft Teams
-   Google Drive
-   CRM systems
-   Enterprise document repositories
-   Existing proposal-management systems
-   Cloud LLM providers
-   Enterprise SSO

These integrations are intentionally outside the initial showcase scope.

## 17. Recommended Repository Structure

``` text
rfp-agent/
│
├── frontend/
│   └── nextjs-app/
│
├── api/
│   └── nodejs/
│
├── ai-service/
│   ├── app/
│   │   ├── agents/
│   │   ├── rag/
│   │   ├── documents/
│   │   ├── embeddings/
│   │   ├── proposal/
│   │   └── api/
│   └── tests/
│
├── ingestion/
│   ├── historical-rfps/
│   └── scripts/
│
├── templates/
│   └── proposal-template.docx
│
├── docker-compose.yml
└── README.md
```

## 18. Hackathon Integration Priority

### Must Have

1.  Next.js UI
2.  Node.js API
3.  Python FastAPI
4.  Ollama
5.  Milvus
6.  PDF/DOCX parsing
7.  Historical RFP ingestion
8.  Requirement extraction
9.  RAG retrieval
10. Evidence-backed response generation
11. Compliance matrix
12. DOCX generation

### Nice to Have

1.  PDF generation
2.  Reranking
3.  OCR
4.  Model comparison
5.  Response scoring
6.  Multilingual support

### Exclude

1.  Kubernetes
2.  Enterprise SSO
3.  Multi-region infrastructure
4.  Production cloud architecture
5.  Automated external RFP submission

## 19. Success Criteria

The showcase should demonstrate one complete journey:

``` text
Upload New RFP
       ↓
Extract 50+ Requirements
       ↓
Search Historical Company Knowledge
       ↓
Generate Evidence-backed Responses
       ↓
Show Sources
       ↓
Identify Knowledge Gaps
       ↓
Human Review
       ↓
Generate Professional Proposal
```

The core message of the showcase should be:

> **Turn historical company RFP knowledge into an intelligent,
> evidence-backed RFP response assistant.**

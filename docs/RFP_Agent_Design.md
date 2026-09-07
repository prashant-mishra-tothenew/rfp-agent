# AI-Powered RFP Response Accelerator --- Design Document

## 1. Purpose

The AI-Powered RFP Response Accelerator is a hackathon/showcase solution
that helps company employees respond to new Requests for Proposal (RFPs)
by reusing approved knowledge from historical RFPs, proposals, case
studies, technical documents, and company capabilities.

The solution is intentionally designed as an internal showcase rather
than a production enterprise platform. It focuses on demonstrating:

-   RFP document understanding
-   Retrieval-Augmented Generation (RAG)
-   Reuse of historical company knowledge
-   Evidence-backed response generation
-   Compliance and gap analysis
-   Human review
-   DOCX/PDF proposal generation
-   Open-source/local AI using Ollama
-   Milvus as the vector database

## 2. Goals

1.  Allow an employee to upload a new RFP.
2.  Extract and classify requirements automatically.
3.  Search historical RFPs and company knowledge.
4.  Generate a draft response using retrieved evidence.
5.  Show the source/evidence behind each generated answer.
6.  Identify requirements for which evidence is missing or weak.
7.  Allow a human to review/edit/approve generated answers.
8.  Generate a professional DOCX and PDF proposal.

## 3. Non-Goals for the Hackathon

The following are intentionally excluded:

-   Kubernetes deployment
-   Production-grade cloud infrastructure
-   Enterprise SSO/OIDC implementation
-   Multi-region deployment
-   S3/MinIO object-storage architecture
-   Production monitoring and observability
-   Automated contractual or legal approval
-   Fully autonomous submission of proposals

The application should run locally or through a simple Docker Compose
setup.

## 4. High-Level Architecture

``` text
+-----------------------------+
|       Employee / User       |
|      Next.js Web UI         |
+--------------+--------------+
               |
               v
+-----------------------------+
|      Node.js / TypeScript   |
|       Application API       |
+--------------+--------------+
               |
               v
+-----------------------------+
|       Python AI Service     |
|          FastAPI            |
+--------------+--------------+
       |        |        |
       |        |        +----------------+
       |        |                         |
       v        v                         v
+----------+ +----------+          +-------------+
| Document | | LangGraph|          |   Milvus    |
| Parser   | | RFP Agent|          | Vector DB   |
+----------+ +----+-----+          +-------------+
                   |
                   v
             +-----------+
             |  Ollama   |
             | Open LLM  |
             +-----------+
```

## 5. Major Components

### 5.1 Frontend

Technology:

-   Next.js
-   React
-   TypeScript

Responsibilities:

-   Upload RFP
-   Display analysis progress
-   Display extracted requirements
-   Display generated responses
-   Display evidence
-   Show confidence/status
-   Allow editing and approval
-   Show compliance/gap dashboard
-   Trigger DOCX/PDF generation

### 5.2 Node.js Application Layer

Technology:

-   Node.js
-   TypeScript
-   NestJS or Fastify

Responsibilities:

-   API gateway for the UI
-   RFP/job management
-   User/session handling for the showcase
-   Workflow coordination
-   Communication with Python AI services
-   Proposal generation requests
-   Serving results to the UI

### 5.3 Python AI Service

Technology:

-   Python
-   FastAPI
-   LangGraph
-   LangChain where useful

Responsibilities:

-   Document processing
-   Requirement extraction
-   RAG orchestration
-   Agent execution
-   LLM calls
-   Evidence retrieval
-   Response generation
-   Compliance analysis
-   Confidence/status calculation

### 5.4 Ollama

Ollama runs the selected open-weight LLM locally.

**Default models** (see `docs/MODEL_SELECTION.md`):

| Role | Model |
|------|-------|
| Chat / solution drafting | `qwen3:32b` |
| Fast routing / classification | `qwen3:8b` |
| Embeddings | `nomic-embed-text` |

Responsibilities:

-   Requirement classification
-   Structured extraction
-   Reasoning
-   Response generation
-   Gap analysis
-   Proposal drafting

The model should be configurable so the project can benchmark multiple
open models without changing the application architecture.

### 5.5 Milvus

Milvus stores embeddings and searchable RFP knowledge.

Recommended knowledge types:

-   Historical RFP requirements
-   Historical approved responses
-   Case studies
-   Technical capabilities
-   Security/compliance information
-   Product/service information
-   Implementation approaches

### 5.6 Relational Database

For the showcase, SQLite or PostgreSQL can be used.

Store:

-   RFP metadata
-   Requirements
-   Generated responses
-   Review status
-   Approval status
-   Source references
-   Proposal versions

## 6. RFP Knowledge Model

Historical RFPs should not be treated as plain documents only. They
should be converted into reusable knowledge units.

Example:

``` json
{
  "requirement": "Solution must support Kubernetes",
  "response": "The proposed solution supports Kubernetes-based deployment...",
  "evidence": "Architecture Document v3.2",
  "industry": "Banking",
  "technology": ["Kubernetes", "AWS"],
  "year": 2025,
  "approved": true,
  "source_document": "RFP-2025-017"
}
```

Important metadata:

-   document_id
-   source_type
-   section
-   industry
-   customer_type
-   geography
-   technology
-   year
-   approval_status
-   confidentiality
-   content_version

## 7. RAG Strategy

The solution should use hybrid retrieval rather than relying only on
semantic similarity.

``` text
New Requirement
      |
      +---- Dense Vector Search ----+
      |                             |
      +---- Sparse/Keyword Search --+--> Candidate Results
                                    |
                                    v
                                Re-ranking
                                    |
                                    v
                              Top Evidence
                                    |
                                    v
                                  LLM
```

This is important for exact RFP terms such as:

-   ISO 27001
-   99.99%
-   RTO 4 hours
-   Kubernetes
-   specific product names
-   certification numbers

## 8. Agent Design

Multi-agent orchestration is implemented with **LangGraph** (`ai-service/app/agents/orchestrator.py`).
The workflow is a directed graph: Analyzer → Knowledge → Response → Compliance → END.

Keep the hackathon implementation to three logical agents plus a deterministic checker.

### RFP Analyzer

Input: New RFP

Output:

-   RFP metadata
-   Requirements
-   Evaluation criteria
-   Mandatory requirements
-   Technical requirements
-   Security requirements
-   Commercial requirements
-   Submission instructions

### Knowledge Agent

Input: Requirement

Output:

-   Relevant historical requirements
-   Previous approved responses
-   Company evidence
-   Case studies
-   Supporting documents

### Response Agent

Input:

-   Current requirement
-   Retrieved evidence
-   Historical responses

Output:

-   New response
-   Evidence references
-   Confidence
-   Status
-   Human-review flag

A deterministic compliance checker should run after generation.

## 9. Evidence-First Generation

The response generator must follow these rules:

1.  Do not blindly copy historical answers.
2.  Adapt responses to the current RFP.
3.  Do not invent company capabilities.
4.  Use only retrieved evidence for factual claims.
5.  Clearly mark insufficient evidence.
6.  Identify content requiring human verification.
7.  Preserve source references.

Example:

``` text
Requirement:
Vendor must provide 99.99% availability.

Generated Response:
Our proposed architecture is designed to support 99.99% availability.

Evidence:
- Architecture Document v3.2
- Approved RFP-2025-017

Confidence:
94%

Status:
Human verification recommended
```

## 10. User Workflow

``` text
Upload RFP
   |
   v
Analyze RFP
   |
   v
Extract Requirements
   |
   v
Retrieve Historical Knowledge
   |
   v
Generate Draft Responses
   |
   v
Compliance / Gap Analysis
   |
   v
Human Review
   |
   v
Generate DOCX
   |
   v
Convert to PDF
```

## 11. Proposal Generation

The LLM should generate structured proposal content rather than directly
controlling document formatting.

``` text
AI Response
    |
    v
Structured Proposal JSON
    |
    v
DOCX Template
    |
    v
python-docx
    |
    v
Proposal.docx
    |
    v
PDF Conversion
```

This provides consistent formatting and makes the generated proposal
easier to review.

## 12. Showcase UI

The primary screen should be simple:

``` text
RFP Assistant

[ Drag & Drop RFP PDF / DOCX ]

Customer: __________
Industry: [ Select ]

[ Analyze RFP ]
```

After analysis:

``` text
RFP Analysis

Requirements             87
Mandatory                48
Covered                  63
Partial                  14
Missing                  10

Response Coverage        72%

[ Generate Draft ]
```

Each requirement should show:

-   Requirement
-   Generated answer
-   Evidence
-   Confidence
-   Status
-   Accept
-   Edit
-   Regenerate

## 13. Key Design Principle

The product should be positioned as:

> AI reuses institutional knowledge safely.

It should not be positioned as:

> AI writes an RFP automatically.

The strongest showcase feature is the ability to explain why an answer
was generated and which company evidence supports it.

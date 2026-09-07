#!/usr/bin/env python3
"""Ingest historical RFP documents into the Milvus knowledge base.

This script parses approved historical PDF/DOCX files, splits them into
semantic chunks, generates embeddings via Ollama, and stores the results in
Milvus for retrieval by the Knowledge Agent during RFP response generation.

Prerequisites:
    - Milvus running (e.g. `docker compose up -d milvus etcd minio`)
    - Ollama running with the embedding model pulled (`nomic-embed-text`)
    - AI service dependencies installed (`pip install -r ai-service/requirements.txt`)

Usage:
    python ingestion/scripts/ingest.py
    python ingestion/scripts/ingest.py --dir ./ingestion/historical-rfps --industry Banking

    Or use the web UI: http://localhost:3000/knowledge

Supported formats: PDF, DOCX
"""

# --- Standard library imports (built into Python, like PHP core extensions) ---
import argparse   # Reads command-line flags (--dir, --industry), similar to getopt() in PHP
import asyncio    # Runs async/await code; like ReactPHP or Swoole coroutines
import os         # File paths and directory checks; like PHP's dirname(), is_dir()
import sys        # Exit codes and Python path; like exit() in PHP
import uuid       # Generates unique IDs; like Ramsey\Uuid in PHP

# Add the ai-service folder to Python's import path so we can reuse its modules.
# Similar to requiring a file outside the current folder in PHP:
#   require_once __DIR__ . '/../ai-service/app/...';
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai-service"))

from app.documents.parser import parse_document   # Extracts text from PDF/DOCX
from app.rag.milvus_store import milvus_store     # Saves chunks + vectors to Milvus DB


async def ingest_file(
    file_path: str,
    document_id: str,
    document_type: str = "historical",
    industry: str = "",
    year: int = 2025,
    approval_status: str = "approved",
) -> int:
    """
    Parse one document and store its chunks in Milvus.

    @param file_path       Full path to a PDF or DOCX file
    @param document_id     Unique name for this document (usually the filename without extension)
    @param document_type   Category label, e.g. "historical", "case_study", "capability"
    @param industry        Industry tag used later for filtering search results
    @param year            Document year (metadata for search/filter)
    @param approval_status Governance flag; only "approved" content should be used for auto-responses
    @return                Number of chunks successfully inserted into Milvus
    """
    # Step 1: Extract plain text from the file (like reading file contents in PHP)
    parsed = parse_document(file_path)
    text = parsed["text"]

    # Step 2: Split long text into smaller pieces (~1500 characters each).
    # LLMs and embedding models work better on smaller chunks, not entire 100-page PDFs.
    chunk_size = 1500
    chunks = []  # PHP equivalent: $chunks = [];

    for i in range(0, len(text), chunk_size):
        chunk_text = text[i : i + chunk_size]  # Slice string: substr($text, $i, $chunk_size)

        if not chunk_text.strip():  # Skip empty chunks (like empty(trim($chunk)) in PHP)
            continue

        # Build one record per chunk — like an associative array in PHP
        chunks.append(
            {
                "id": str(uuid.uuid4()),           # Unique chunk ID (primary key in Milvus)
                "document_id": document_id,
                "document_type": document_type,
                "section": f"chunk-{i // chunk_size + 1}",  # f-string ≈ "chunk-" . ($i / $chunk_size + 1)
                "content": chunk_text,
                "industry": industry,
                "technology": "",
                "year": year,
                "approval_status": approval_status,
                "confidentiality": "internal",
                "source_page": i // chunk_size + 1,
            }
        )

    # Step 3: Embed each chunk and insert into Milvus (async = non-blocking I/O)
    return await milvus_store.insert_chunks(chunks)


async def ingest_directory(dir_path: str, industry: str = "Technology") -> None:
    """
    Loop through all PDF/DOCX files in a folder and ingest each one.

    @param dir_path  Folder path containing historical documents
    @param industry  Default industry tag applied to every file in this folder
    @return          None (prints progress to the console)
    """
    supported = {".pdf", ".docx"}  # Set of allowed extensions (like an array_flip whitelist in PHP)
    total = 0

    # os.listdir() ≈ scandir() / glob in PHP; sorted() keeps output predictable
    for filename in sorted(os.listdir(dir_path)):
        ext = os.path.splitext(filename)[1].lower()  # Get ".pdf" or ".docx" from filename

        if ext not in supported:
            continue  # Skip unsupported files (like continue in PHP foreach)

        file_path = os.path.join(dir_path, filename)       # Full path: $dir . '/' . $filename
        doc_id = os.path.splitext(filename)[0]             # Filename without extension

        count = await ingest_file(file_path, doc_id, industry=industry)
        total += count
        print(f"  Ingested {count} chunks from {filename}")

    print(f"\nTotal chunks ingested: {total}")


def main():
    """
    Entry point when you run: python ingestion/scripts/ingest.py

    Reads CLI arguments, validates the folder exists, then starts ingestion.
    (PHP equivalent: a script block at the bottom of a CLI file, or a main() function)
    """
    # Define accepted command-line options (like getopt() or Symfony Console Input)
    parser = argparse.ArgumentParser(description="Ingest historical RFPs into Milvus")
    parser.add_argument(
        "--dir",
        default="./ingestion/historical-rfps",
        help="Directory containing historical PDF/DOCX files",
    )
    parser.add_argument("--industry", default="Technology")
    args = parser.parse_args()  # $args = parse command line into an object

    if not os.path.isdir(args.dir):
        print(f"Directory not found: {args.dir}")
        print("Place historical RFP PDFs/DOCX files in ingestion/historical-rfps/")
        sys.exit(1)  # Exit with error code 1, same as exit(1) in PHP

    print(f"Ingesting from: {args.dir}")

    # asyncio.run() starts the async event loop and waits until ingest_directory() finishes.
    # Similar to running an async PHP script with ReactPHP: Loop::run(...)
    asyncio.run(ingest_directory(args.dir, args.industry))


# Only run main() when this file is executed directly, not when imported as a module.
# PHP equivalent: if (php_sapi_name() === 'cli' && basename(__FILE__) === basename($_SERVER['argv'][0]))
if __name__ == "__main__":
    main()

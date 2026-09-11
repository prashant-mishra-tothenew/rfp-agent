from pathlib import Path

from pydantic_settings import BaseSettings

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _data_path(subdir: str) -> str:
    return str(_REPO_ROOT / "data" / subdir)


class Settings(BaseSettings):
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:32b"
    llm_fast_model: str = "qwen3:8b"
    analyzer_model: str = ""  # defaults to llm_fast_model when empty
    analyzer_max_chars: int = 20000
    embedding_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://localhost:11434"

    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "rfp_knowledge"

    upload_dir: str = _data_path("uploads")
    proposal_dir: str = _data_path("proposals")
    template_path: str = str(_REPO_ROOT / "templates" / "proposal-template.docx")
    pptx_template_path: str = str(_REPO_ROOT / "templates" / "proposal-template.pptx")
    ollama_timeout_seconds: float = 900.0
    pipeline_max_requirements: int = 25
    pipeline_concurrency: int = 3
    response_batch_size: int = 3
    response_model: str = ""
    response_evidence_items: int = 3
    response_evidence_chars: int = 600
    response_max_tokens: int = 400
    retrieval_score_threshold: float = 0.55
    proposal_model: str = ""
    proposal_concurrency: int = 3
    proposal_max_tokens: int = 500
    proposal_response_chars: int = 150
    proposal_max_responses: int = 25
    proposal_generate_pdf: bool = False
    proposal_pdf_timeout_seconds: int = 30

    class Config:
        env_file = str(_REPO_ROOT / ".env")
        extra = "ignore"


settings = Settings()

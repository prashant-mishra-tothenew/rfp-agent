from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:32b"
    llm_fast_model: str = "qwen3:8b"
    embedding_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://localhost:11434"

    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "rfp_knowledge"

    upload_dir: str = "/app/data/uploads"
    proposal_dir: str = "/app/data/proposals"
    template_path: str = "/app/templates/proposal-template.docx"
    ollama_timeout_seconds: float = 900.0
    pipeline_max_requirements: int = 25

    class Config:
        env_file = ".env"


settings = Settings()

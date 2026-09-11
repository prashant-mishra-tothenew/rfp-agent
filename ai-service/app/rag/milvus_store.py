from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.config import settings
from app.embeddings.service import embed_text

EMBEDDING_DIM = 768


class MilvusStore:
    def __init__(self):
        self.collection_name = settings.milvus_collection
        self._connected = False

    def connect(self) -> None:
        if self._connected:
            return
        connections.connect(
            alias="default",
            host=settings.milvus_host,
            port=settings.milvus_port,
        )
        self._connected = True
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if utility.has_collection(self.collection_name):
            return

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="document_type", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="industry", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="technology", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="year", dtype=DataType.INT64),
            FieldSchema(name="approval_status", dtype=DataType.VARCHAR, max_length=32),
            FieldSchema(name="confidentiality", dtype=DataType.VARCHAR, max_length=32),
            FieldSchema(name="source_page", dtype=DataType.INT64),
            FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        ]
        schema = CollectionSchema(fields, description="RFP historical knowledge")
        Collection(name=self.collection_name, schema=schema)

        collection = Collection(self.collection_name)
        collection.create_index(
            field_name="dense_vector",
            index_params={
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128},
            },
        )

    @property
    def collection(self) -> Collection:
        self.connect()
        return Collection(self.collection_name)

    @staticmethod
    def _escape_expr_string(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def delete_by_document_id(self, document_id: str) -> int:
        """Remove all Milvus chunks for a knowledge document."""
        if not document_id:
            return 0

        self.collection.load()
        expr = f'document_id == "{self._escape_expr_string(document_id)}"'
        result = self.collection.delete(expr)
        self.collection.flush()
        return int(getattr(result, "delete_count", 0) or 0)

    async def insert_chunks(self, chunks: list[dict[str, Any]]) -> int:
        if not chunks:
            return 0

        vectors = [await embed_text(c["content"]) for c in chunks]
        data = [
            [c["id"] for c in chunks],
            [c.get("document_id", "") for c in chunks],
            [c.get("document_type", "historical") for c in chunks],
            [c.get("section", "") for c in chunks],
            [c["content"] for c in chunks],
            [c.get("industry", "") for c in chunks],
            [c.get("technology", "") for c in chunks],
            [c.get("year", 0) for c in chunks],
            [c.get("approval_status", "approved") for c in chunks],
            [c.get("confidentiality", "internal") for c in chunks],
            [c.get("source_page", 0) for c in chunks],
            vectors,
        ]
        self.collection.insert(data)
        self.collection.flush()
        return len(chunks)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        query_vector = await embed_text(query)
        expr = self._build_filter_expr(filters)
        self.collection.load()

        results = self.collection.search(
            data=[query_vector],
            anns_field="dense_vector",
            param={"metric_type": "COSINE", "params": {"nprobe": 16}},
            limit=top_k * 2,
            expr=expr,
            output_fields=[
                "document_id",
                "document_type",
                "section",
                "content",
                "industry",
                "technology",
                "year",
                "approval_status",
                "confidentiality",
                "source_page",
            ],
        )

        hits: list[dict[str, Any]] = []
        for hit in results[0]:
            entity = hit.entity
            hits.append(
                {
                    "id": hit.id,
                    "score": float(hit.score),
                    "document_id": entity.get("document_id"),
                    "document_type": entity.get("document_type"),
                    "section": entity.get("section"),
                    "content": entity.get("content"),
                    "industry": entity.get("industry"),
                    "technology": entity.get("technology"),
                    "year": entity.get("year"),
                    "approval_status": entity.get("approval_status"),
                    "confidentiality": entity.get("confidentiality"),
                    "source_page": entity.get("source_page"),
                }
            )

        # Keyword boost for exact RFP terms (ISO, SLA, product names)
        keyword_boosted = self._keyword_boost(query, hits)
        return keyword_boosted[:top_k]

    def _build_filter_expr(self, filters: dict[str, Any] | None) -> str | None:
        if not filters:
            return None
        parts: list[str] = []
        if filters.get("approved"):
            # Exclude draft/expired only; include historical reference docs
            # (response agent still flags weak matches for human review).
            parts.append(
                'approval_status in ["approved", "current", "historical"]'
            )
        if industry := filters.get("industry"):
            parts.append(f'industry == "{industry}"')
        return " and ".join(parts) if parts else None

    @staticmethod
    def _keyword_boost(query: str, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        query_lower = query.lower()
        keywords = [w for w in query_lower.split() if len(w) > 3]

        for hit in hits:
            content_lower = (hit.get("content") or "").lower()
            boost = sum(0.05 for kw in keywords if kw in content_lower)
            hit["score"] = min(1.0, hit["score"] + boost)

        return sorted(hits, key=lambda h: h["score"], reverse=True)


milvus_store = MilvusStore()

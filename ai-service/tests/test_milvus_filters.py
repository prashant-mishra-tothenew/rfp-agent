from app.rag.milvus_store import MilvusStore


def test_approved_filter_includes_historical_reference_docs():
    store = MilvusStore()
    expr = store._build_filter_expr({"approved": True, "industry": "Technology"})
    assert 'approval_status in ["approved", "current", "historical"]' in expr
    assert 'industry == "Technology"' in expr


def test_no_filter_when_empty():
    store = MilvusStore()
    assert store._build_filter_expr(None) is None
    assert store._build_filter_expr({}) is None

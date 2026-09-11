from app.rag.milvus_store import MilvusStore


def test_escape_expr_string_handles_quotes():
    store = MilvusStore()
    escaped = store._escape_expr_string('TRAIN-"001"')
    assert escaped == 'TRAIN-\\"001\\"'

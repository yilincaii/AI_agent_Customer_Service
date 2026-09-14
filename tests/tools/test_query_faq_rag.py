from unittest.mock import AsyncMock
async def test_dense_faq_returns_numbered_evidence(monkeypatch):
    from app.tools.builtin.faq import query_faq
    monkeypatch.setattr("app.core.retrieval.search_knowledge",AsyncMock(return_value=[{"id":1,"section_path":"policy","question":"returns","answer":"7 days","content_type":"policy"}]))
    out=await query_faq.ainvoke({"keyword":"returns"})
    assert out["sufficient"] and out["citations"][0]["n"]==1
    assert "[1]" in out["evidence"]
async def test_empty_faq_is_insufficient(monkeypatch):
    from app.tools.builtin.faq import query_faq
    monkeypatch.setattr("app.core.retrieval.search_knowledge",AsyncMock(return_value=[]))
    out=await query_faq.ainvoke({"keyword":"unknown"})
    assert not out["sufficient"] and not out["citations"]

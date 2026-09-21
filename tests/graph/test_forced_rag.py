from unittest.mock import AsyncMock
from langchain_core.messages import HumanMessage
from app.graph import nodes

async def test_knowledge_path_rejects_missing_evidence(monkeypatch):
    monkeypatch.setattr(nodes.query_understanding,"understand",AsyncMock(return_value={"standard":"q","expanded":[]}))
    monkeypatch.setattr(nodes.retrieval,"search_knowledge",AsyncMock(return_value=[]))
    out=await nodes.retrieve_knowledge({"messages":[HumanMessage("q")]})
    assert out["evidence_strong"] is False
async def test_knowledge_path_builds_numbered_evidence(monkeypatch):
    monkeypatch.setattr(nodes.query_understanding,"understand",AsyncMock(return_value={"standard":"q","expanded":[]}))
    monkeypatch.setattr(nodes.retrieval,"search_knowledge",AsyncMock(return_value=[{"id":1,"rerank_score":1.,"question":"q","answer":"a","section_path":"p","content_type":"policy"}]))
    monkeypatch.setattr(nodes.selfcheck,"check_sufficient",AsyncMock(return_value={"useful":True}))
    out=await nodes.retrieve_knowledge({"messages":[HumanMessage("q")]})
    assert out["evidence_strong"] and out["citations"][0]["n"]==1 and "[1]" in out["evidence"]

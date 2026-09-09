import json
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk


@pytest.fixture
def client():
    from app.main import app
    from app.api import chat as chat_api
    chat_api.store._sessions.clear()
    return TestClient(app)


def payloads(response):
    return [json.loads(line[6:]) for line in response.text.splitlines()
            if line.startswith("data: ") and line != "data: [DONE]"]


def test_streams_sse_frames_and_retains_session_history(client, monkeypatch):
    from app.api import chat as chat_api
    received=[]
    class Model:
        async def astream(self, messages):
            received.append(messages)
            yield AIMessageChunk(content="Hello")
            yield AIMessageChunk(content=" there")
    monkeypatch.setattr(chat_api,"get_chat_model",lambda **kwargs: Model())
    response=client.post("/api/chat",json={"session_id":"a","message":"hi"})
    assert response.status_code==200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [p["delta"] for p in payloads(response)]==["Hello"," there"]
    assert response.text.endswith("data: [DONE]\n\n")
    client.post("/api/chat",json={"session_id":"a","message":"again"})
    assert [m.content for m in received[1] if m.type=="human"]==["hi","again"]
    assert [m.content for m in received[1] if m.type=="ai"]==["Hello there"]


def test_sessions_do_not_share_history(client, monkeypatch):
    from app.api import chat as chat_api
    received=[]
    class Model:
        async def astream(self,messages):
            received.append(messages)
            yield AIMessageChunk(content="OK")
    monkeypatch.setattr(chat_api,"get_chat_model",lambda **kwargs: Model())
    client.post("/api/chat",json={"session_id":"a","message":"private-a"})
    client.post("/api/chat",json={"session_id":"b","message":"hello-b"})
    assert [m.content for m in received[1] if m.type=="human"]==["hello-b"]


def test_empty_message_is_rejected(client):
    assert client.post("/api/chat",json={"message":""}).status_code==422


def test_upstream_failure_returns_error_without_private_details(client,monkeypatch):
    from app.api import chat as chat_api
    class Model:
        async def astream(self,messages):
            raise RuntimeError("test-private-detail")
            yield
    monkeypatch.setattr(chat_api,"get_chat_model",lambda **kwargs: Model())
    response=client.post("/api/chat",json={"message":"hi"})
    assert "event: error" in response.text
    assert "test-private-detail" not in response.text
    assert chat_api.store.get("default")==[]


def test_chat_page_is_available(client):
    response=client.get("/")
    assert response.status_code==200
    assert "text/html" in response.headers["content-type"]

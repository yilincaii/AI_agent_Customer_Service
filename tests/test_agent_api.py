from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

@pytest.fixture
def agent(monkeypatch):
    import app.api.agent as api
    monkeypatch.setattr(api.repository,"create_conversation",AsyncMock(return_value=1))
    monkeypatch.setattr(api.repository,"get_conversation",AsyncMock(return_value=None))
    monkeypatch.setattr(api.repository,"list_messages",AsyncMock(return_value=[]))
    monkeypatch.setattr(api.repository,"append_message",AsyncMock(return_value=1))
    monkeypatch.setattr(api,"get_all_specs",AsyncMock(return_value=[]))
    return api

async def test_direct_agent_answers_and_persists(agent,monkeypatch):
    class Model:
        def bind_tools(self,tools):return self
        async def ainvoke(self,messages):return AIMessage(content="Hello")
    monkeypatch.setattr(agent,"get_chat_model",lambda:Model())
    from app.schemas.agent import AgentRequest
    out=await agent.run_agent(AgentRequest(user_id="u1",message="hi"))
    assert out.answer=="Hello" and out.conversation_id==1
    assert agent.repository.append_message.await_count==2

async def test_agent_rejects_missing_conversation(agent):
    from app.schemas.agent import AgentRequest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:await agent.run_agent(AgentRequest(user_id="u1",message="hi",conversation_id=99))
    assert e.value.status_code==404

async def test_agent_bounds_repeated_tool_calls(agent,monkeypatch):
    class Model:
        count=0
        def bind_tools(self,tools):return self
        async def ainvoke(self,messages):
            self.count+=1
            return AIMessage(content="",tool_calls=[{"id":str(self.count),"name":"missing","args":{}}])
    model=Model();monkeypatch.setattr(agent,"get_chat_model",lambda:model)
    from app.schemas.agent import AgentRequest
    out=await agent.run_agent(AgentRequest(user_id="u1",message="hi"))
    assert model.count==agent.settings.max_agent_steps
    assert len(out.tool_results)==model.count and not any(r.ok for r in out.tool_results)

# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

import pytest

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.graph import nodes

def test_agent_messages_no_evidence_on_business():
    msgs = nodes._agent_messages({"route": "business", "messages": [HumanMessage("订单1001")]})
    assert isinstance(msgs[0], SystemMessage)
    assert all("已检索到的知识证据" not in (m.content or "") for m in msgs)  # 整个列表都不该有

@pytest.fixture()
def builtin_only_specs(monkeypatch):
    """ch08:节点每轮现拉内置+MCP;单测锚定为仅内置,免网络依赖。"""
    from app.tools import registry

    async def only_builtin():
        return registry.builtin_specs()

    monkeypatch.setattr(nodes.registry, "get_all_specs", only_builtin)

@pytest.mark.asyncio
async def test_main_agent_accumulates_steps_and_tokens(monkeypatch, builtin_only_specs):
    ai = AIMessage("好的", usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})

    class FakeModel:
        def bind_tools(self, tools):
            return self
        def bind(self, **kwargs):
            return self
        async def ainvoke(self, msgs, config=None):
            return ai

    monkeypatch.setattr(nodes, "get_chat_model", lambda **k: FakeModel())
    out = await nodes.main_agent({"messages": [HumanMessage("hi")], "steps": 1, "tokens_used": 100})
    assert out["steps"] == 2
    assert out["tokens_used"] == 115
    assert out["messages"][0] is ai

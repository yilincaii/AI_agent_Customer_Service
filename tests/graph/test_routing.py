from langchain_core.messages import AIMessage
from app.graph.routing import should_continue
from app.config import settings

def test_agent_loop_stops_at_limit():
    ai=AIMessage("",tool_calls=[{"id":"1","name":"query_order","args":{}}])
    assert should_continue({"messages":[ai],"steps":settings.max_agent_steps})=="stop"
    assert should_continue({"messages":[AIMessage("done")],"steps":0})=="stop"
    assert should_continue({"messages":[ai],"steps":0})=="continue"

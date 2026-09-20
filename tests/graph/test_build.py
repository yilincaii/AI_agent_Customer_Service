from langchain_core.messages import AIMessage,HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from app.graph.build import build_graph
from app.graph import nodes

async def test_graph_invokes_and_records_answer(monkeypatch):
    async def model_step(state,config=None):return {"messages":[AIMessage("hello")],"steps":1}
    async def no_log(state):return {}
    monkeypatch.setattr(nodes,"main_agent",model_step);monkeypatch.setattr(nodes,"log_node",no_log)
    graph=build_graph(InMemorySaver())
    out=await graph.ainvoke({"messages":[HumanMessage("hi")],"steps":0},{"configurable":{"thread_id":"1"}})
    assert nodes.resolve_answer(out)=="hello" and out["steps"]==1

def test_graph_registered_nodes_compile():
    names=set(build_graph().get_graph().nodes)
    assert {"main_agent","agent_tools","log"}<=names

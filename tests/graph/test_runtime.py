import pytest
from langchain_core.messages import AIMessage,HumanMessage
from app.graph import runtime,nodes

async def test_checkpoint_reuses_history_and_resets_trace(monkeypatch):
    monkeypatch.setattr(runtime.settings,"checkpointer_db_path",":memory:")
    async def reply(state,config=None):return {"messages":[AIMessage("hello")],"steps":1}
    async def no_log(state):return {}
    monkeypatch.setattr(nodes,"main_agent",reply);monkeypatch.setattr(nodes,"log_node",no_log)
    await runtime.init_graph()
    try:
        graph=runtime.get_graph();config={"configurable":{"thread_id":"42"}}
        first=await graph.ainvoke({"messages":[HumanMessage("one")],"trace":{"first":1}},config)
        second=await graph.ainvoke({"messages":[HumanMessage("two")],"trace":None},config)
        assert len(second["messages"])==4 and second["trace"]=={}
    finally:await runtime.close_graph()

def test_graph_input_resets_output_channels():
    x=runtime._graph_input("u1","hi",1,1,"",0)
    assert x["answer"]=="" and x["trace"] is None and x["steps"]==0

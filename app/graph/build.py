from langgraph.graph import END,START,StateGraph
from app.graph import nodes
from app.graph.routing import should_continue
from app.graph.state import ConversationState

def _builder():
    b=StateGraph(ConversationState)
    for name,fn in [("main_agent",nodes.main_agent),("agent_tools",nodes.agent_tools),("log",nodes.log_node)]:b.add_node(name,fn)
    b.add_edge(START,"main_agent")
    b.add_conditional_edges("main_agent",should_continue,{"continue":"agent_tools","stop":"log"})
    b.add_edge("agent_tools","main_agent")
    b.add_edge("log",END)
    return b

def build_graph(checkpointer=None):return _builder().compile(checkpointer=checkpointer)

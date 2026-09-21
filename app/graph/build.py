from langgraph.graph import END,START,StateGraph
from app.graph import nodes
from app.graph.routing import should_continue
from app.graph.state import ConversationState

def _builder():
    b=StateGraph(ConversationState)
    for name,fn in [("main_agent",nodes.main_agent),("agent_tools",nodes.agent_tools),("log",nodes.log_node)]:b.add_node(name,fn)
    from app.graph.routing import confidence_gate,route_by_intent
    for name in ["retrieve_knowledge","confidence_check","script_reply","complaint_reply","fallback_reply"]:b.add_node(name,getattr(nodes,name))
    b.add_edge("retrieve_knowledge","confidence_check")
    b.add_conditional_edges("confidence_check",confidence_gate,{"strong":"main_agent","weak":"fallback_reply"})
    for name in ["script_reply","complaint_reply","fallback_reply"]:b.add_edge(name,"log")
    b.add_conditional_edges(START,route_by_intent,{"escalate":"complaint_reply","fallback_script":"script_reply","knowledge":"retrieve_knowledge","business":"main_agent"})
    b.add_conditional_edges("main_agent",should_continue,{"continue":"agent_tools","stop":"log"})
    b.add_edge("agent_tools","main_agent")
    b.add_edge("log",END)
    return b

def build_graph(checkpointer=None):return _builder().compile(checkpointer=checkpointer)

import logging
from langchain_core.messages import AIMessage,HumanMessage,SystemMessage,ToolMessage
from app.config import settings
from app.core.llm import get_chat_model
from app.core.prompts import AGENT_SYSTEM
from app.db import repository
from app.tools import registry,engine
logger=logging.getLogger(__name__)

def _user_text(state):
    return next((m.content for m in reversed(state.get("messages",[])) if isinstance(m,HumanMessage)),"")
def _history_text(state,max_turns=6):
    return "\n".join(f"{m.type}:{m.content}" for m in state.get("messages",[])[:-1][-max_turns:])
def _agent_messages(state):
    return [SystemMessage(AGENT_SYSTEM),*state.get("messages",[])]
async def main_agent(state,config=None):
    specs=await registry.get_all_specs()
    ai=await get_chat_model(streaming=True).bind_tools([s.tool for s in specs]).ainvoke(_agent_messages(state),config)
    used=(ai.usage_metadata or {}).get("total_tokens",0)
    return {"messages":[ai],"steps":state.get("steps",0)+1,"tokens_used":state.get("tokens_used",0)+used}
async def agent_tools(state):
    specs={s.name:s for s in await registry.get_all_specs()}
    results=[]
    for call in state["messages"][-1].tool_calls:
        run=await engine.execute_tool_call(call,state.get("conversation_id",0),specs,user_id=state.get("user_id",""))
        results.append(run.tool_message)
    return {"messages":results}

# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

def resolve_answer(state) -> str:
    """最终答复:确定性节点写在 state['answer'];Agent 答复取最后一条 AIMessage 文本。"""
    if state.get("answer"):
        return state["answer"]
    for m in reversed(state.get("messages", [])):
        if isinstance(m, AIMessage):
            content = m.content
            if isinstance(content, str):
                return content
            return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""

async def log_node(state) -> dict:
    """日志记录:留痕 intent/route/trace(可观测地基),并落 MySQL 一条 assistant 消息(审计)。"""
    logger.info(
        "turn conv=%s intent=%s route=%s resolved=%r trace=%s",
        state.get("conversation_id"), state.get("intent"), state.get("route"),
        state.get("resolved_query"), state.get("trace", {}),
    )
    answer = resolve_answer(state)
    if state.get("conversation_id"):
        await repository.append_message(state["conversation_id"], "assistant",
                                        content=answer or None)
    return {}

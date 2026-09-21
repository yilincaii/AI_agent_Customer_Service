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
    msgs=[SystemMessage(AGENT_SYSTEM),*state.get("messages",[])]
    if state.get("evidence"):
        msgs.append(HumanMessage("已检索到的知识证据，请引用编号，不再调用 query_faq:\n"+state["evidence"]))
    return msgs
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

from app.core import query_understanding,retrieval,selfcheck
from app.core.prompts import COMPLAINT_REPLY_TEXT,FALLBACK_REPLY_TEXT,SCRIPT_REPLY_CHITCHAT,SCRIPT_REPLY_OTHER
COMPLAINT_REPLY=COMPLAINT_REPLY_TEXT
FALLBACK_REPLY=FALLBACK_REPLY_TEXT

async def retrieve_knowledge(state):
    query=state.get("resolved_query") or _user_text(state)
    u=await query_understanding.understand(query)
    hits=await retrieval.search_knowledge(u["standard"],strategy="hybrid_rerank",bm25_text=u["standard"]+" "+" ".join(u["expanded"]))
    if not hits or hits[0]["rerank_score"]<settings.rerank_min_score:
        return {"evidence_strong":False,"trace":{"forced_rag":True}}
    chk=await selfcheck.check_sufficient(u["standard"],[h["question"]+" "+h["answer"] for h in hits])
    if not chk["useful"]:return {"evidence_strong":False,"trace":{"forced_rag":True}}
    citations=[{"n":i+1,"id":h["id"],"section_path":h["section_path"],"question":h["question"],"answer":h["answer"],"content_type":h["content_type"]} for i,h in enumerate(retrieval.arrange_head_tail(hits))]
    return {"evidence_strong":True,"citations":citations,"evidence":"\n".join(f"[{c['n']}] {c['question']}: {c['answer']}" for c in citations),"trace":{"forced_rag":True}}
async def confidence_check(state):return {"trace":{"confidence":"strong" if state.get("evidence_strong") else "weak"}}
async def fallback_reply(state):
    await repository.insert_low_confidence(state.get("conversation_id"),_user_text(state),"retrieval_low_conf","Evidence insufficient")
    return {"answer":FALLBACK_REPLY,"suggested_actions":[{"type":"transfer_human"}],"trace":{"route":"fallback"}}

# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

async def script_reply(state) -> dict:
    """fallback_script 出口:闲聊/其他 兜底话术(零模型),按 intent 分文案——闲聊把话题引回产品,
    其他请用户说具体些。分流后立即命中、不进 Agent。
    (与 ch05 知识路证据弱的 fallback_reply 是两码事,名字相近但不同节点、不同触发点,勿混。)"""
    text = SCRIPT_REPLY_OTHER if state.get("intent") == "其他" else SCRIPT_REPLY_CHITCHAT
    return {"answer": text, "trace": {"route": "fallback_script"}}

async def complaint_reply(state) -> dict:
    """投诉:安抚话术 + 转人工/建工单两个可选项(后端不执行,交前端自选)。"""
    actions = [
        {"type": "transfer_human"},
        {"type": "create_ticket",
         "draft": {"description": _user_text(state), "ticket_type": "投诉"}},
    ]
    return {"answer": COMPLAINT_REPLY, "suggested_actions": actions,
            "trace": {"route": "complaint"}}

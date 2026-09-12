from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.exc import SQLAlchemyError
from app.config import settings
from app.core.llm import get_chat_model
from app.core.prompts import AGENT_PROMPT
from app.db import repository
from app.tools.registry import get_all_specs
from app.tools.engine import execute_tool_call
from app.schemas.agent import AgentRequest,AgentResponse,ToolCallView,ToolResultView
router=APIRouter()

@router.post("/api/agent",response_model=AgentResponse)
async def run_agent(req:AgentRequest):
    try:
        cid=req.conversation_id
        if cid is not None:
            conv=await repository.get_conversation(cid)
            if conv is None or conv.user_id!=req.user_id: raise HTTPException(404,"会话不存在")
        else: cid=await repository.create_conversation(req.user_id)
        history=await repository.list_messages(cid)
        messages=[HumanMessage(content=m.content or "") if m.role=="user" else AIMessage(content=m.content or "") for m in history if m.role in ("user","assistant")]
        messages.append(HumanMessage(content=req.message))
        specs={s.name:s for s in await get_all_specs()}
        model=get_chat_model().bind_tools([s.tool for s in specs.values()])
        calls=[];results=[];answer="工具调用已达到上限，请稍后重试。"
        for _ in range(settings.max_agent_steps):
            response=await model.ainvoke(AGENT_PROMPT.invoke({"history":messages}).to_messages())
            messages.append(response)
            if not response.tool_calls: answer=str(response.content);break
            for tc in response.tool_calls:
                calls.append(ToolCallView(id=tc["id"],name=tc["name"],args=tc["args"]))
                run=await execute_tool_call(tc,cid,specs,user_id=req.user_id)
                messages.append(run.tool_message)
                results.append(ToolResultView(tool_call_id=run.tool_call_id,name=run.name,ok=run.ok,content=run.tool_message.content))
        await repository.append_message(cid,"user",content=req.message)
        await repository.append_message(cid,"assistant",content=answer)
        return AgentResponse(conversation_id=cid,answer=answer,tool_calls=calls,tool_results=results)
    except HTTPException: raise
    except SQLAlchemyError: raise HTTPException(503,"数据库暂时不可用")
    except Exception: raise HTTPException(502,"上游模型暂时不可用")

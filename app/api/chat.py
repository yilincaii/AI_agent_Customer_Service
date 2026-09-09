# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com
import json
from collections.abc import AsyncIterator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from app.config import settings
from app.core.llm import get_chat_model
from app.core.memory import SessionStore, trim_history
from app.core.prompts import CUSTOMER_SERVICE_PROMPT
from app.schemas.chat import ChatRequest

router=APIRouter()
store=SessionStore()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload,ensure_ascii=False)}\n\n"


@router.post("/api/chat")
async def chat(req: ChatRequest):
    async def event_stream() -> AsyncIterator[str]:
        user=HumanMessage(req.message)
        history=trim_history([*store.get(req.session_id),user],settings.token_budget)
        messages=CUSTOMER_SERVICE_PROMPT.format_messages(history=history)
        answer=[]
        try:
            model=get_chat_model(streaming=True)
            async for chunk in model.astream(messages):
                if isinstance(chunk.content,str) and chunk.content:
                    answer.append(chunk.content)
                    yield _sse({"delta":chunk.content})
        except Exception:
            yield "event: error\n"
            yield _sse({"message":"上游模型暂时不可用,请稍后重试"})
            yield "data: [DONE]\n\n"
            return
        store.append(req.session_id,user,AIMessage(''.join(answer)))
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(),media_type="text/event-stream")

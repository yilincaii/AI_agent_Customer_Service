# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.chat import router as chat_router
from app.api.extract import router as extract_router

from contextlib import asynccontextmanager
from app.graph import runtime
@asynccontextmanager
async def lifespan(app):
    _check_context_budget()
    await runtime.init_graph()
    try:yield
    finally:await runtime.close_graph()
app=FastAPI(title="MewHelp",version="0.1.0",lifespan=lifespan)
app.include_router(chat_router)
app.include_router(extract_router)
_STATIC_DIR=Path(__file__).parent/"static"
app.mount("/static",StaticFiles(directory=_STATIC_DIR),name="static")


@app.get("/",include_in_schema=False)
async def chat_page() -> FileResponse:
    return FileResponse(_STATIC_DIR/"index.html")

from app.api.agent import router as agent_router
app.include_router(agent_router)

from app.api.kb import router as kb_router
app.include_router(kb_router)

@app.get("/kb")
def kb_page():
    return FileResponse(Path(__file__).parent / "static" / "kb.html")

from app.api.jobs import router as jobs_router
app.include_router(jobs_router)

from app.api.rageval import router as rageval_router
app.include_router(rageval_router)

@app.get("/rag-eval")
def rageval_page():
    return FileResponse(Path(__file__).parent / "static" / "rageval.html")

from app.api.actions import router as actions_router
app.include_router(actions_router)

from app.api.conversations import router as conversations_router
app.include_router(conversations_router)

from app.core import budget
from app.config import settings
# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

def _check_context_budget() -> None:
    """启动自检:算一遍上下文预算,装不下一轮就报警,别等运行时撞墙。"""
    from app.core import budget
    b = budget.compute()
    if b.healthy:
        logger.info("上下文预算 %s", budget.describe(b))
    else:
        logger.error("上下文预算不足:窗口 %s 装不下 固定开销 %s + 单轮 ReAct 峰值 %s。"
                     "换窗口更大的模型,或调小 MAX_AGENT_STEPS / TOOL_RESULT_MAX_TOKENS / "
                     "MAX_OUTPUT_TOKENS / RERANK_TOP_K。%s",
                     b.window, b.fixed, b.peak, budget.describe(b))

import logging
logger=logging.getLogger(__name__)

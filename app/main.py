# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.chat import router as chat_router

app=FastAPI(title="MewHelp",version="0.1.0")
app.include_router(chat_router)
_STATIC_DIR=Path(__file__).parent/"static"
app.mount("/static",StaticFiles(directory=_STATIC_DIR),name="static")


@app.get("/",include_in_schema=False)
async def chat_page() -> FileResponse:
    return FileResponse(_STATIC_DIR/"index.html")

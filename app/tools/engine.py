from dataclasses import dataclass
import json
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from langchain_core.messages import ToolMessage
from app.tools.registry import ToolSpec

@dataclass
class ToolRun:
    tool_call_id: str
    name: str
    ok: bool
    tool_message: ToolMessage
    status: str

def validate_args(spec: ToolSpec,args: dict):
    err=best_match(Draft202012Validator(spec.json_schema).iter_errors(args))
    return err.message if err else None

async def execute_tool_call(tool_call,conversation_id,specs,*,user_id="",confirmed=False,deny_note=None):
    name=tool_call.get("name",""); ident=tool_call.get("id",""); args=dict(tool_call.get("args") or {})
    try:
        spec=specs.get(name)
        if spec is None: raise ValueError("Unknown tool")
        error=validate_args(spec,args)
        if error: raise ValueError(error)
        if spec.permission=="write" and not confirmed: raise PermissionError("User confirmation required")
        if spec.inject_conversation: args["conversation_id"]=conversation_id
        if spec.inject_user_id: args["user_id"]=user_id
        out=await spec.tool.ainvoke(args)
        content=json.dumps(out,ensure_ascii=False,default=str);ok=True;status="成功"
    except Exception as e:
        content=str(e);ok=False;status="权限拒绝" if isinstance(e,PermissionError) else "失败"
    return ToolRun(ident,name,ok,ToolMessage(content=content,tool_call_id=ident,name=name or "unknown",status="success" if ok else "error"),status)

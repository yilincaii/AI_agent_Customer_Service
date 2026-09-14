from langchain_core.tools import tool
from pydantic import BaseModel,Field
from app.core import retrieval
from app.tools import registry
class FaqInput(BaseModel):
    keyword:str=Field(description="Policy question")
    category:str|None=None
@tool(args_schema=FaqInput)
async def query_faq(keyword:str,category:str|None=None)->dict:
    """Retrieve policy evidence with numbered citations."""
    hits=await retrieval.search_knowledge(keyword,strategy="vector",category=category)
    citations=[{"n":i+1,"id":h["id"],"section_path":h["section_path"],"question":h["question"],"answer":h["answer"],"content_type":h["content_type"]} for i,h in enumerate(retrieval.arrange_head_tail(hits))]
    return {"sufficient":bool(citations),"evidence":"\n".join(f"[{c['n']}] {c['question']}: {c['answer']}" for c in citations),"citations":citations}
registry.register(registry.spec_from_langchain_tool(query_faq,source="builtin"))

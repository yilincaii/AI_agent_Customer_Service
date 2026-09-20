# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

def merge_dict(a: dict | None, b: dict | None) -> dict:
    """trace 累加 reducer:后写覆盖同键,其余合并;b 为 None 是重置哨兵。
    入口(_graph_input)每轮传 trace=None 清零本轮 trace——merge 通道塞 {} 清不掉
    (merge(旧,{})=旧),故用 None 触发重置,杜绝上一轮条件键(如 retrieve_policy)跨轮残留。
    图内各节点写 trace 恒为真 dict(从不传 None),故 None 专属入口重置,不误伤累加。"""
    if b is None:
        return {}
    return {**(a or {}), **b}

class ConversationState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: str
    conversation_id: int
    evidence: str
    citations: list
    answer: str
    steps: int
    tokens_used: int
    suggested_actions: list
    trace: Annotated[dict, merge_dict]

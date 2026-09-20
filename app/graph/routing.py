# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

from langchain_core.messages import AIMessage

from app.config import settings

def should_continue(state) -> str:
    """ReAct 停止条件:无 tool_calls 就收敛,步数封顶则强停,否则继续。

    只用步数封顶,不在这里卡 token。防打转靠的是步数:一步一次模型调用,数得清、好解释,
    各家 Agent SDK 给的也是 max_turns / max_iterations 这类步数上限。
    token 花销是另一件事——它管的是烧钱和撑爆上下文,不是死循环,阈值要按真实用量分布标定,
    归第 9 章的成本控制一起讲。混在这里卡,一次估偏就把工具链整条掐断,而且掐在模型
    已经决定调工具之后,用户只看到半句「我这就去查」。"""
    last = state["messages"][-1]
    has_tool_calls = isinstance(last, AIMessage) and bool(last.tool_calls)
    if not has_tool_calls:
        return "stop"
    if state.get("steps", 0) >= settings.max_agent_steps:
        return "stop"
    return "continue"

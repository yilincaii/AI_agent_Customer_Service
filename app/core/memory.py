# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com
from langchain_core.messages import BaseMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages

# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

def count_tokens(messages) -> int:
    """估算这批消息的 token。

    count_tokens_approximately 默认 chars_per_token=4.0 是按英文定的,中文一个字往往
    就是一个 token,照默认口径算会低估四倍(实测 29 个汉字被估成 12)。裁剪、预算判断
    都走这一个入口,口径才对得齐。"""
    return count_tokens_approximately(
        messages, chars_per_token=1.2)

class SessionStore:
    """内存会话存储,session_id -> 消息列表。本章不做持久化。"""

    def __init__(self) -> None:
        self._sessions: dict[str, list[BaseMessage]] = {}

    def get(self, session_id: str) -> list[BaseMessage]:
        return self._sessions.get(session_id, [])

    def append(self, session_id: str, *messages: BaseMessage) -> None:
        self._sessions.setdefault(session_id, []).extend(messages)

def trim_history(messages: list[BaseMessage], max_tokens: int) -> list[BaseMessage]:
    return trim_messages(
        messages,
        strategy="last",
        token_counter=count_tokens,
        max_tokens=max_tokens,
        start_on="human",
        allow_partial=False,
    )

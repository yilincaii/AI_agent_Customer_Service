# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com
import logging
from langchain_core.exceptions import OutputParserException
from langchain_openai import ChatOpenAI
from app.config import settings
_TRUTHY = {'1', 'true', 'yes', 'on'}

def get_chat_model(streaming: bool=False, model: str | None=None, temperature: float | None=None, slot: str='chat', thinking: bool=True) -> ChatOpenAI:
    """直连聊天上游,说 OpenAI 协议。
    model 显式覆盖模型名(意图识别可配更大模型求准),None 时回落 settings.chat_model。
    ch09:usage 统一收口——流式也回传 token(等效 stream_options.include_usage),
    否则 Langfuse 按意图统计只有非流式调用的账,主力 Agent 全漏。

    temperature 默认 0.3(答用户的话要有点人味)。**当评委用的链路要显式传 0**:
    同一份证据+同一份答案,0.3 下重放四次给出过 5/6、5/6、6/6、6/6 三种结果,
    量出来的分数里就混进了采样噪声——评估要的是可复现,不是多样性。

    thinking=False 显式关闭思考链。structured() 用它:DeepSeek 的 thinking 和
    tool_choice 指定函数互斥(官方文档:思考模式下不支持 required 和指定具体 tool),
    结构化输出走 function_calling 必须关。不能只是不传——DeepSeek 默认 thinking 开着,
    不传等于开,所以 False 时显式发 disabled。"""
    slot_model, base_url, api_key = resolve_slot(slot)
    thinking_kw = _thinking_kwargs() if thinking else {'extra_body': {'thinking': {'type': 'disabled'}}}
    return ChatOpenAI(model=model or slot_model, base_url=base_url, api_key=api_key, streaming=streaming, stream_usage=False, max_tokens=settings.max_output_tokens, temperature=0.3 if temperature is None else temperature, **thinking_kw)

def _thinking_kwargs() -> dict:
    """把三项思考链配置拼成 ChatOpenAI 的参数。留空的不传,交给上游默认。

    thinking 和 reasoning_split 不是 OpenAI 协议里的标准字段,得走 extra_body;
    reasoning_effort 是标准字段,ChatOpenAI 直接认。上游不认的参数会被静默忽略
    (给不认 thinking.type 的上游传过去,既不报错也不生效),所以这里不按 provider 分叉。"""
    kwargs: dict = {}
    extra: dict = {}
    if settings.chat_thinking:
        extra['thinking'] = {'type': settings.chat_thinking}
    if settings.chat_reasoning_split:
        extra['reasoning_split'] = settings.chat_reasoning_split.strip().lower() in _TRUTHY
    if extra:
        kwargs['extra_body'] = extra
    if settings.chat_reasoning_effort:
        kwargs['reasoning_effort'] = settings.chat_reasoning_effort
    return kwargs

def resolve_slot(slot: str='chat') -> tuple[str, str, str]:
    """按用途取 (模型名, 地址, key)。intent / summary 各是一个槽位,三项分别留空就
    回落 CHAT 那组——只用一家上游时它们一个都不用填,想把某个用途换到别家才填。"""
    if slot == 'chat':
        return (settings.chat_model, settings.chat_base_url, settings.chat_api_key)
    return (getattr(settings, f'{slot}_model', '') or settings.chat_model, getattr(settings, f'{slot}_base_url', '') or settings.chat_base_url, getattr(settings, f'{slot}_api_key', '') or settings.chat_api_key)
logger = logging.getLogger(__name__)
_NO_STREAM_TOOLCALL_FAMILIES: tuple[str, ...] = ('minimax',)

def needs_non_streaming_tools(model: str | None=None, slot: str='chat') -> bool:
    name = (model or resolve_slot(slot)[0] or '').lower()
    return any((f in name for f in _NO_STREAM_TOOLCALL_FAMILIES))

def structured(schema, *, model: str | None=None, streaming: bool=True, temperature: float | None=None, slot: str='chat'):
    """要结构化结果就用这个,别直接 with_structured_output——它默认走 json_schema,
    那条路解析正文,会被模型多吐的思考正文带崩。

    默认开流式:中转的非流式 OpenAI 兼容层会把 tool_calls 的 arguments 拼坏,流式不会
    (见上面那段注释里的实测)。

    只有 function calling 一条通路。偶发失败原样重试一次,再不成就把异常抛给调用点——
    调用点各自降级成安全默认值,别在这里降级到一条更差的通路上。

    temperature 透传给底层模型:当评委用的结构化链路传 0(见 get_chat_model 的说明)。
    """
    from langchain_core.runnables import RunnableLambda
    slot_model, slot_base, _ = resolve_slot(slot)
    name = (model or slot_model or '').lower()
    if needs_non_streaming_tools(model, slot=slot):
        streaming = False
    m = get_chat_model(streaming=streaming, model=model, temperature=temperature, slot=slot, thinking=False)
    fc = m.with_structured_output(schema, method='function_calling')

    def _log(attempt: int, why: str) -> None:
        logger.warning('%s 经 %s 的 function calling 第 %s 次没成(%s),%s', name, slot_base, attempt, why, '原样重试一次' if attempt == 1 else '抛给调用点')

    def _no_tool_calls() -> OutputParserException:
        return OutputParserException(f'{name} 经 {settings.chat_base_url} 连着两次都没返回 tool_calls')

    def _run(x):
        for attempt in (1, 2):
            try:
                r = fc.invoke(x)
            except Exception as e:
                _log(attempt, type(e).__name__)
                if attempt == 2:
                    raise
                continue
            if r is not None:
                return r
            _log(attempt, '响应里没有 tool_calls')
        raise _no_tool_calls()

    async def _arun(x):
        for attempt in (1, 2):
            try:
                r = await fc.ainvoke(x)
            except Exception as e:
                _log(attempt, type(e).__name__)
                if attempt == 2:
                    raise
                continue
            if r is not None:
                return r
            _log(attempt, '响应里没有 tool_calls')
        raise _no_tool_calls()
    return RunnableLambda(_run, afunc=_arun)

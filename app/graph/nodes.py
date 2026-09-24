import json
import logging
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from app.config import settings
from app.core.llm import get_chat_model
from app.core.prompts import AGENT_SYSTEM
from app.db import repository
from app.tools import registry, engine
logger = logging.getLogger(__name__)

def _user_text(state):
    return next((m.content for m in reversed(state.get('messages', [])) if isinstance(m, HumanMessage)), '')

def _history_text(state, max_turns=6):
    return '\n'.join((f'{m.type}:{m.content}' for m in state.get('messages', [])[:-1][-max_turns:]))

async def main_agent(state, config=None):
    specs = await registry.get_all_specs()
    ai = await get_chat_model(streaming=True).bind_tools([s.tool for s in specs]).ainvoke(_agent_messages(state), config)
    used = (ai.usage_metadata or {}).get('total_tokens', 0)
    return {'messages': [ai], 'steps': state.get('steps', 0) + 1, 'tokens_used': state.get('tokens_used', 0) + used}

def resolve_answer(state) -> str:
    """最终答复:确定性节点写在 state['answer'];Agent 答复取最后一条 AIMessage 文本。"""
    if state.get('answer'):
        return state['answer']
    for m in reversed(state.get('messages', [])):
        if isinstance(m, AIMessage):
            content = m.content
            if isinstance(content, str):
                return content
            return ''.join((p.get('text', '') for p in content if isinstance(p, dict)))
    return ''

async def log_node(state) -> dict:
    """日志记录:留痕 intent/route/trace(可观测地基),并落 MySQL 一条 assistant 消息(审计)。"""
    logger.info('turn conv=%s intent=%s route=%s resolved=%r trace=%s', state.get('conversation_id'), state.get('intent'), state.get('route'), state.get('resolved_query'), state.get('trace', {}))
    answer = resolve_answer(state)
    if state.get('conversation_id'):
        await repository.append_message(state['conversation_id'], 'assistant', content=answer or None)
    return {}
from app.core import query_understanding, retrieval, selfcheck
from app.core.prompts import COMPLAINT_REPLY_TEXT, FALLBACK_REPLY_TEXT, SCRIPT_REPLY_CHITCHAT, SCRIPT_REPLY_OTHER
COMPLAINT_REPLY = COMPLAINT_REPLY_TEXT
FALLBACK_REPLY = FALLBACK_REPLY_TEXT

async def retrieve_knowledge(state):
    query = state.get('resolved_query') or _user_text(state)
    u = await query_understanding.understand(query)
    hits = await retrieval.search_knowledge(u['standard'], strategy='hybrid_rerank', bm25_text=u['standard'] + ' ' + ' '.join(u['expanded']))
    if not hits or hits[0]['rerank_score'] < settings.rerank_min_score:
        return {'evidence_strong': False, 'trace': {'forced_rag': True}}
    chk = await selfcheck.check_sufficient(u['standard'], [h['question'] + ' ' + h['answer'] for h in hits])
    if not chk['useful']:
        return {'evidence_strong': False, 'trace': {'forced_rag': True}}
    citations = [{'n': i + 1, 'id': h['id'], 'section_path': h['section_path'], 'question': h['question'], 'answer': h['answer'], 'content_type': h['content_type']} for i, h in enumerate(retrieval.arrange_head_tail(hits))]
    return {'evidence_strong': True, 'citations': citations, 'evidence': '\n'.join((f'[{c['n']}] {c['question']}: {c['answer']}' for c in citations)), 'trace': {'forced_rag': True}}

async def confidence_check(state):
    return {'trace': {'confidence': 'strong' if state.get('evidence_strong') else 'weak'}}

async def fallback_reply(state):
    await repository.insert_low_confidence(state.get('conversation_id'), _user_text(state), 'retrieval_low_conf', 'Evidence insufficient')
    return {'answer': FALLBACK_REPLY, 'suggested_actions': [{'type': 'transfer_human'}], 'trace': {'route': 'fallback'}}

async def script_reply(state) -> dict:
    """fallback_script 出口:闲聊/其他 兜底话术(零模型),按 intent 分文案——闲聊把话题引回产品,
    其他请用户说具体些。分流后立即命中、不进 Agent。
    (与 ch05 知识路证据弱的 fallback_reply 是两码事,名字相近但不同节点、不同触发点,勿混。)"""
    text = SCRIPT_REPLY_OTHER if state.get('intent') == '其他' else SCRIPT_REPLY_CHITCHAT
    return {'answer': text, 'trace': {'route': 'fallback_script'}}

async def complaint_reply(state) -> dict:
    """投诉:安抚话术 + 转人工/建工单两个可选项(后端不执行,交前端自选)。"""
    actions = [{'type': 'transfer_human'}, {'type': 'create_ticket', 'draft': {'description': _user_text(state), 'ticket_type': '投诉'}}]
    return {'answer': COMPLAINT_REPLY, 'suggested_actions': actions, 'trace': {'route': 'complaint'}}
from app.core import coref
from app.core import intent as intent_mod
from app.graph.routing import INTENT_TO_ROUTE

async def resolve_reference(state) -> dict:
    """指代消解 + Query 改写(合一):吃最近几轮历史把半截话补成完整问句;已完整则透传。
    写 resolved_query,供 classify_intent 与 refund_flow 检索共用(意图识别不再改写)。"""
    query = _user_text(state)
    history = _history_text(state)
    logger.info('history_ctx conv=%s(摘要行+滑窗,coref/意图共用)\n%s', state.get('conversation_id'), history or '(无历史)')
    resolved = await coref.resolve(query, history)
    mode = 'rewrite' if resolved != query else 'passthrough'
    return {'resolved_query': resolved, 'trace': {'coref': mode}}

async def classify_intent(state) -> dict:
    """意图四件套:八类 + confidence + 「其他」兜底。吃 resolved_query(空则回落原话)+ 最近历史
    判当前意图(应对物流→退款→物流漂移)。把归属出口 route 落进 State(供 _agent_messages 判注入、
    log 留痕;route_by_intent 条件边按同一 INTENT_TO_ROUTE 分流,单一来源不漂移)。"""
    query = state.get('resolved_query') or _user_text(state)
    r = await intent_mod.classify(query, _history_text(state))
    intent, conf = (r['intent'], r['confidence'])
    route = INTENT_TO_ROUTE.get(intent, 'business')
    return {'intent': intent, 'intent_confidence': conf, 'route': route, 'trace': {'intent': intent, 'intent_confidence': conf, 'route': route}}
import re
from langgraph.types import interrupt
from app.tools import business
_ORDER_RE = re.compile('(?<!\\d)(\\d{4,})(?!\\d)')

def _extract_order_id(text: str) -> str | None:
    m = _ORDER_RE.search(text or '')
    return m.group(1) if m else None

async def fetch_order(state) -> dict:
    """退款子流程第一步:抽订单号;缺了、或者报的不是自己的单,都 interrupt 弹订单选择器
    等前端点选(resume 回填);拿到后 order_snapshot 取订单数据。
    interrupt 之前只做只读(resume 时本节点从头重跑)。

    归属校验放在这里而不是只放在工具里:退款子流程是确定性节点,不经 agent_tools,
    工具那道校验够不着。用户随口报的号、resume 端点回传的号,都得过同一道判断。"""
    uid = state.get('user_id', '')
    oid = state.get('order_id') or _extract_order_id(state.get('resolved_query') or _user_text(state))
    while not business.owns_order(uid, str(oid or '')):
        orders = business.list_user_orders(uid)
        oid = interrupt({'type': 'select_order', 'orders': orders})
    data = business.order_snapshot(oid)
    return {'order_id': oid, 'order_data': data, 'trace': {'fetch_order': {'order_id': oid}}}

async def retrieve_policy(state) -> dict:
    """退款子流程强制检索政策:Query 扩写 3 条 → 多 query 各检索一次 → 按 chunk id 去重合并
    (保留每 id 最高分)→ 按分降序拼编号证据。产出注入 main_agent 作「能不能退」的判据(README L194:
    不让模型凭记忆答)。库里知识一份,扩写只在检索侧现查现用。"""
    base = state.get('resolved_query') or _user_text(state)
    od = state.get('order_data') or {}
    seed = f'{base} {od.get('status', '')}'.strip()
    queries = await query_understanding.expand_queries(seed)
    merged: dict = {}
    for q in queries:
        for h in await retrieval.search_knowledge(q, strategy='hybrid_rerank', bm25_text=q):
            cur = merged.get(h['id'])
            if cur is None or h['rerank_score'] > cur['rerank_score']:
                merged[h['id']] = h
    ranked = sorted(merged.values(), key=lambda h: h['rerank_score'], reverse=True)
    arranged = retrieval.arrange_head_tail(ranked)
    citations = [{'n': i + 1, 'id': h['id'], 'section_path': h['section_path'], 'question': h['question'], 'answer': h['answer'], 'content_type': h['content_type']} for i, h in enumerate(arranged)]
    evidence = '\n'.join((f'[{c['n']}] {c['question']}: {c['answer']}' for c in citations))
    return {'evidence': evidence, 'citations': citations, 'trace': {'retrieve_policy': {'queries': queries, 'hits': len(ranked)}}}

async def agent_tools(state) -> dict:
    """ReAct 行动步(ch08):一切工具经统一执行引擎。create_ticket(唯一写操作)走确认流——
    参数齐则节点顶部 interrupt 推工单预览(interrupt 前只做纯计算,resume 重跑安全,照 fetch_order
    范式);参数缺则交引擎按「校验拦下」回灌,模型自然向用户追问,不弹卡。
    submit_refund 仍拦成前端退款表单(ch06 语义不变)。"""
    last = state['messages'][-1]
    cid = state.get('conversation_id', 0)
    uid = state.get('user_id', '')
    specs = {s.name: s for s in await registry.get_all_specs()}
    ticket_calls = [tc for tc in last.tool_calls if tc['name'] == 'create_ticket']
    tspec = specs.get('create_ticket')
    decision = None
    tool_msgs = []
    actions = list(state.get('suggested_actions', []))
    not_owned = False
    for tc in last.tool_calls:
        if tc['name'] == 'submit_refund':
            if not business.owns_order(uid, str(tc['args'].get('order_id') or '')):
                not_owned = True
                tool_msgs.append(ToolMessage(content='没有找到这位用户的这笔订单,本次不发起退款。请如实告知没查到,并让用户从下面列出的订单里选一笔,不要再调用任何工具。', tool_call_id=tc['id'], name='submit_refund', status='error'))
                continue
            actions.append({'type': 'refund_form', 'draft': {'order_id': tc['args'].get('order_id', ''), 'reason': tc['args'].get('reason')}})
            tool_msgs.append(ToolMessage(content='已把『提交退款工单』选项交给用户确认。请用一句话说明这一单可以退款并停止,不要再调用任何工具。', tool_call_id=tc['id'], name='submit_refund'))
        else:
            run = await engine.execute_tool_call(tc, cid, specs, user_id=uid)
            if tc['name'] == 'query_order' and (not business.owns_order(uid, str((tc.get('args') or {}).get('order_id') or ''))):
                not_owned = True
            tool_msgs.append(run.tool_message)
    if not_owned:
        actions.append({'type': 'select_order', 'orders': business.list_user_orders(uid)})
    out = {'messages': tool_msgs}
    if actions:
        out['suggested_actions'] = actions
    return out
from app.core.prompts import REFUND_JUDGE_HINT
# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

_KNOWLEDGE_EVIDENCE_HINT = (
    "\n\n## 已检索到的知识证据(请据此作答,每个关键结论后标注来源编号如[1];"
    "证据已给,不要再调用 query_faq;仍可按需调用订单/物流等工具)\n"
    "型号编号逐字复制证据里的写法,证据里没有的型号不要写;带条件的结论要连条件一起说。\n"
)

def _turn_context(state) -> str:
    """本轮才有的材料:检索证据 + 退款路的订单数据。没有就返回空串。

    顺序不能反:REFUND_JUDGE_HINT 的措辞是「下面给出该订单数据与检索到的退换货政策证据」,
    它假设证据已在前文给过。"""
    parts = []
    if state.get("evidence"):
        parts.append(_KNOWLEDGE_EVIDENCE_HINT + state["evidence"])
    if state.get("route") == "refund_flow":
        parts.append(REFUND_JUDGE_HINT + json.dumps(state.get("order_data", {}), ensure_ascii=False))
    return "".join(parts)     # 三段文本逐字沿用原来的常量,一个字都不改:这次只挪位置,

TURN_CTX_ID = "turn-ctx"   # 哨兵:日志里据此把注入块跟真实用户消息分开。只能用 id 不能用 name

def _with_turn_context(window: list, turn_ctx: str) -> list:
    """把本轮材料插在滑窗里最后一条用户消息之后。

    插在这个位置而不是整个列表末尾,是为了 ReAct 轮内也能命中前缀缓存:第 2 步的
    [Sys, 用户问, 材料, AI, Tool] 完整包含第 1 步的 [Sys, 用户问, 材料] 作前缀;
    追加到末尾则第 2 步变成 [Sys, 用户问, AI, Tool, 材料],公共前缀只到用户问那条。
    窗口里没有用户消息(极端裁剪回退分支)时退化成追加到末尾,不抛异常。"""
    msg = HumanMessage(turn_ctx, id=TURN_CTX_ID)
    for i in range(len(window) - 1, -1, -1):
        if isinstance(window[i], HumanMessage):
            return [*window[:i + 1], msg, *window[i + 1:]]
    return [*window, msg]

def _agent_messages(state):
    window=list(state.get("messages",[]))
    context=_turn_context(state)
    if context:window=_with_turn_context(window,context)
    return [SystemMessage(AGENT_SYSTEM),*window]

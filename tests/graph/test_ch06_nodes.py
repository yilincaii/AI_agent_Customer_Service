import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from app.graph import nodes

@pytest.mark.asyncio
async def test_classify_intent_writes_confidence_and_route(monkeypatch):

    async def fake_classify(query, history=''):
        return {'intent': '退款退货', 'confidence': 0.83}
    monkeypatch.setattr(nodes.intent_mod, 'classify', fake_classify)
    out = await nodes.classify_intent({'messages': [HumanMessage('这个能退吗')], 'resolved_query': '蓝牙耳机还能申请退货吗'})
    assert out['intent'] == '退款退货'
    assert out['intent_confidence'] == 0.83
    assert out['route'] == 'business'
    assert out['trace']['route'] == 'business'
    assert out['trace']['intent_confidence'] == 0.83

def test_get_chat_model_honors_model_override():
    from app.core.llm import get_chat_model
    m = get_chat_model(model='glm-4-flash')
    assert m.model_name == 'glm-4-flash'
    d = get_chat_model()
    from app.config import settings
    assert d.model_name == settings.chat_model

@pytest.mark.asyncio
async def test_resolve_reference_passthrough_when_complete(monkeypatch):

    async def fake_resolve(q, history=''):
        return q
    monkeypatch.setattr(nodes.coref, 'resolve', fake_resolve)
    out = await nodes.resolve_reference({'messages': [HumanMessage('蓝牙耳机的保修期多久')]})
    assert out['resolved_query'] == '蓝牙耳机的保修期多久'
    assert out['trace']['coref'] == 'passthrough'

@pytest.mark.asyncio
async def test_resolve_reference_rewrites_with_history(monkeypatch):

    async def fake_resolve(q, history=''):
        return '蓝牙耳机还能申请退货吗'
    monkeypatch.setattr(nodes.coref, 'resolve', fake_resolve)
    out = await nodes.resolve_reference({'messages': [HumanMessage('蓝牙耳机什么时候到'), AIMessage('预计明天'), HumanMessage('这个能退吗')]})
    assert out['resolved_query'] == '蓝牙耳机还能申请退货吗'
    assert out['trace']['coref'] == 'rewrite'

def test_list_user_orders_stable_and_queryable():
    from app.tools import business
    a = business.list_user_orders('u-42')
    b = business.list_user_orders('u-42')
    assert a == b and len(a) >= 2
    snap = business.order_snapshot(a[0]['order_id'])
    assert snap['order_id'] == a[0]['order_id'] and snap['product'] == a[0]['product']

def test_agent_messages_knowledge_path_still_injects_evidence():
    msgs = nodes._agent_messages({'route': 'knowledge', 'evidence': '[1] 运费: 满99包邮', 'messages': [HumanMessage('运费多少')]})
    assert '满99包邮' not in msgs[0].content
    assert '满99包邮' in msgs[-1].content

@pytest.mark.asyncio
async def test_script_reply_by_intent():
    from app.core.prompts import SCRIPT_REPLY_CHITCHAT, SCRIPT_REPLY_OTHER
    chit = await nodes.script_reply({'intent': '闲聊'})
    assert chit['answer'] == SCRIPT_REPLY_CHITCHAT
    assert chit['trace']['route'] == 'fallback_script'
    other = await nodes.script_reply({'intent': '其他'})
    assert other['answer'] == SCRIPT_REPLY_OTHER

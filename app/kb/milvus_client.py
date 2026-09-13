import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from pymilvus import AnnSearchRequest, DataType, Function, FunctionType, MilvusClient, RRFRanker
from app.config import settings
COLLECTION = 'knowledge'
DIM = 1024
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='milvus')

async def acall(fn, *args, **kwargs):
    """在专用单线程上执行同步 pymilvus 调用(供 async 在线路径用)。"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_EXECUTOR, functools.partial(fn, *args, **kwargs))
_CLIENT: MilvusClient | None = None
_ensured: set[str] = set()
_OUTPUT = ['question', 'answer', 'section_path', 'content_type', 'category']

def get_client(uri: str | None=None) -> MilvusClient:
    """默认返回进程内单例(连 Standalone);传 uri(测试)返回独立客户端。"""
    global _CLIENT
    if uri is not None:
        return MilvusClient(uri=uri)
    if _CLIENT is None:
        _CLIENT = MilvusClient(uri=settings.milvus_uri)
    return _CLIENT

def ensure_collection(client: MilvusClient, collection: str=COLLECTION) -> None:
    """幂等建集合:dense(COSINE) + text(chinese analyzer) + sparse(BM25 Function) + 标量字段。
    单例默认集合只实际执行一次;不同集合名(测试临时库)各自 ensure。"""
    if client is _CLIENT and collection in _ensured:
        return
    if client.has_collection(collection):
        client.load_collection(collection)
    else:
        schema = client.create_schema(auto_id=False)
        schema.add_field('id', DataType.INT64, is_primary=True)
        schema.add_field('dense', DataType.FLOAT_VECTOR, dim=DIM)
        schema.add_field('question', DataType.VARCHAR, max_length=2048)
        schema.add_field('answer', DataType.VARCHAR, max_length=8192)
        schema.add_field('section_path', DataType.VARCHAR, max_length=512)
        schema.add_field('content_type', DataType.VARCHAR, max_length=32)
        schema.add_field('category', DataType.VARCHAR, max_length=255)
        index_params = client.prepare_index_params()
        index_params.add_index(field_name='dense', index_type='AUTOINDEX', metric_type='COSINE')
        client.create_collection(collection, schema=schema, index_params=index_params)
        client.load_collection(collection)
    if client is _CLIENT:
        _ensured.add(collection)

def upsert_vectors(client: MilvusClient, rows: list[dict], collection: str=COLLECTION) -> None:
    if rows:
        client.upsert(collection, rows)

def flush(client: MilvusClient, collection: str=COLLECTION) -> None:
    """刷盘:新 upsert 的数据须 flush 后才可被 BM25/检索命中(Task 1 实证)。"""
    client.flush(collection)

def _cat_expr(category: str | None) -> str:
    return f'category == "{category}"' if category else ''

def _hit(h: dict) -> dict:
    e = h['entity']
    return {'id': h['id'], 'score': float(h['distance']), 'question': e['question'], 'answer': e['answer'], 'section_path': e['section_path'], 'content_type': e['content_type'], 'category': e['category']}

def dense_search(client, vector, top_k, category=None, collection=COLLECTION) -> list[dict]:
    res = client.search(collection, data=[vector], anns_field='dense', limit=top_k, output_fields=_OUTPUT, search_params={'metric_type': 'COSINE'}, filter=_cat_expr(category))
    return [_hit(h) for h in res[0]]

def count(client, collection: str=COLLECTION) -> int:
    return client.query(collection, filter='id >= 0', output_fields=['count(*)'])[0]['count(*)']

def drop(client, collection: str) -> None:
    if client.has_collection(collection):
        client.drop_collection(collection)

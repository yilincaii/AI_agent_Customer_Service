from app.core import embeddings
from app.kb import milvus_client

def arrange_head_tail(items):
    return items if len(items)<=2 else [items[0],*items[2:],items[1]]

async def search_knowledge(query,strategy="vector",top_k=10,category=None,client=None,collection="knowledge",**kwargs):
    if strategy!="vector":raise ValueError("Only vector retrieval is available")
    vec=await embeddings.embed_query(query)
    def work():
        c=client or milvus_client.get_client()
        milvus_client.ensure_collection(c,collection=collection)
        return milvus_client.dense_search(c,vec,top_k,category,collection)
    return await milvus_client.acall(work)

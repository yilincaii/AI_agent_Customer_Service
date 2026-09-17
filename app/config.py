# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    chat_model: str
    chat_base_url: str
    chat_api_key: str
    chat_thinking: str = ""
    chat_reasoning_effort: str = ""
    chat_reasoning_split: str = ""
    token_budget: int = 2000
    max_output_tokens: int = 10000

    database_url: str = ""  # 必须通过 DATABASE_URL 提供，不内置数据库凭据
    test_database_url: str = ""  # 必须通过 TEST_DATABASE_URL 提供
    max_agent_steps: int = 6              # ReAct 环最大步数(封顶,超则兜底)
    embed_base_url: str = "https://api.siliconflow.cn/v1"
    embed_api_key: str
    embed_model: str = "BAAI/bge-m3"          # 上游真实名(无网关别名可用)
    milvus_uri: str = "http://localhost:19530"   # ch04: Lite → Standalone
    rerank_base_url: str = "https://api.siliconflow.cn/v1"
    rerank_api_key: str
    rerank_model: str = "BAAI/bge-reranker-v2-m3"   # 上游真实名
    recall_top_k: int = 50        # dense/BM25 各召回 Top-50
    rerank_top_k: int = 10        # 精排出 Top-10
    subquery_split: bool = True   # 一问多意图时按子句拆开各检索一遍再轮转合并(见 retrieval)
    rerank_min_score: float = 0.3 # 重排最高分低于此 → 检索证据低,拒答

settings = Settings()

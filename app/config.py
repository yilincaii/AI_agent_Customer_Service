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
    checkpointer_db_path: str = "data/ch05_checkpoints.sqlite"  # LangGraph checkpointer(data/*.db* 已 gitignore)
    intent_base_url: str = ""         # 空=回落 chat_base_url
    intent_api_key: str = ""          # 空=回落 chat_api_key
    intent_model: str = ""            # 意图识别模型名;空=回落 chat_model
    intent_small_model: str = ""      # 降级路小模型(种子,未接运行时)
    intent_mode: str = "accuracy"     # accuracy=只用大模型;cost=小模型判→低置信升级大模型(未实现)
    intent_conf_threshold: float = 0.6  # cost 模式升级阈值(种子)
    summary_inject_segments: int = 3        # 注入时带最近几段摘要
    summary_base_url: str = ""        # 空=回落 chat_base_url
    summary_api_key: str = ""         # 空=回落 chat_api_key
    context_window_max_tokens: int = 0    # 滑窗 token 上限。0=按 core/budget 的预算算,
    summary_model: str = ""               # 摘要模型,空=回落 chat_model
    model_context_window: int = 0           # 模型窗口。留 0 表示按 chat_model 名字查表(见 core/budget),
    context_budget_turns: int = 20          # 预算按多少轮的最坏情况留;这个量以内的对话不会被裁掉
    max_user_input_tokens: int = 2000       # X:单轮用户输入上限,约 1400 汉字
    system_prompt_tokens: int = 700         # 实测:AGENT_SYSTEM 208 + 5 个内置工具 schema 476
    evidence_tokens_per_chunk: int = 160    # 实测:answer 99 字 + 问法 10 + 标题路径 20,加编号格式
    layer1_ratio: float = 0.7               # 层 1(原文)占滑窗预算的比例,其余归层 2
    layer2_reply_keep_chars: int = 60       # 降到层 2 的客服答复留多少字,首句通常就是结论
    layer2_tool_keep_tokens: int = 200      # 工具结果小于这个数就原样留,大块的压成一行
    tool_result_max_tokens: int = 3000    # 单条工具结果回灌模型的硬上限,执行引擎按它截断。
    agent_step_ai_tokens: int = 500       # ReAct 中间步 AI 消息的估值:tool_call 参数,
    summary_tokens_per_segment: int = 250   # 每段摘要的估算体积,几十到两百字
    budget_safety_margin: int = 1000        # 估算误差余量
    zh_chars_per_token: float = 1.2
    tool_default_timeout: float = 5.0    # 内置工具默认超时(秒)
    mcp_tool_timeout: float = 10.0       # MCP 工具默认超时(走 HTTP,放宽)
    tool_max_retries: int = 2            # 只读工具暂时性故障最大重试次数
    demo_ticket_delay_seconds: float = 0.0  # 验收 6:>0 时 create_ticket 人为变慢(写超时演示)
    mcp_logistics_url: str = "http://127.0.0.1:8101/mcp"    # 物流 MCP Server
    mcp_aftersales_url: str = "http://127.0.0.1:8102/mcp"   # 售后 MCP Server
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = ""     # 如 http://localhost:3000(自部署地址,数据不出门)
    evidence_confidence_threshold: float = 0.30

settings = Settings()

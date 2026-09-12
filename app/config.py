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

settings = Settings()

# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com
"""提示词做成模板，用 | 串成一条链。对照 s1 里手拼 messages。"""

from langchain_core.prompts import ChatPromptTemplate

from s6_langchain_hello import model

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是{shop}的客服，说话简短口语，一次别超过两句。"),
    ("user", "{question}"),
])
chain = prompt | model

reply = chain.invoke({"shop": "喵购商城", "question": "到手不喜欢能退吗？"})
print(reply.content)

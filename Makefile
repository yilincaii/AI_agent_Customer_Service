export PYTHONUTF8 = 1
.PHONY: dev test
dev:
	bash scripts/dev.sh
test:
	uv run pytest
eval:
	PYTHONPATH=. uv run python scripts/eval_extract.py
db-up:
	docker compose up -d mysql
eval-agent:
	PYTHONPATH=. uv run python scripts/eval_agent.py
kb-preview:
	PYTHONPATH=. uv run python scripts/show_kb.py
kb-build:
	PYTHONPATH=. uv run python scripts/build_kb.py
kb-vectorize:
	PYTHONPATH=. uv run python scripts/vectorize_kb.py
kb-repatch:
	PYTHONPATH=. uv run python scripts/kb_repatch.py
eval-retrieval:
	PYTHONPATH=. uv run python scripts/eval_retrieval.py
kb-mine:
	PYTHONPATH=. uv run python scripts/mine_knowledge.py
eval-rag:
	PYTHONPATH=. uv run python scripts/eval_ch04.py
eval-check:
	PYTHONPATH=. uv run python scripts/validate_eval_ch04.py
judge-check:
	PYTHONPATH=. uv run python scripts/judge_check.py
eval-workflow:
	PYTHONPATH=. uv run python scripts/eval_ch06.py
eval-context:
	PYTHONPATH=. uv run python scripts/eval_ch07.py

mcp-up:
	@mkdir -p log data
	@nohup uv run python mcp_servers/logistics_server.py  > log/mcp-logistics.log 2>&1 & echo $$! > data/mcp-logistics.pid
	@nohup uv run python mcp_servers/aftersales_server.py > log/mcp-aftersales.log 2>&1 & echo $$! > data/mcp-aftersales.pid
	@sleep 1 && echo "MCP Servers 已拉起: logistics=:8101 aftersales=:8102(pid 见 data/*.pid)"


mcp-down:
	-@kill `cat data/mcp-logistics.pid 2>/dev/null` 2>/dev/null; rm -f data/mcp-logistics.pid
	-@kill `cat data/mcp-aftersales.pid 2>/dev/null` 2>/dev/null; rm -f data/mcp-aftersales.pid
	@echo "MCP Servers 已停"


eval-ch08:  ## ch08 验收样例端到端(需 make dev 全服务 + MCP Server 在跑 + 已应用 sql/ch08-ddl.sql)
	uv run python -m scripts.eval_ch08

langfuse-up:
	docker compose -p mewhelp-langfuse -f docker-compose.langfuse.yml up -d
	@echo "Langfuse 起中: http://localhost:3000 (admin@mewhelp.local / mewhelp123)"
	@echo "首次就绪约 2-3 分钟;key 已 headless 预置,写 .env:"
	@echo "  LANGFUSE_PUBLIC_KEY=pk-lf-mewhelp-local"
	@echo "  LANGFUSE_SECRET_KEY=sk-lf-mewhelp-local"
	@echo "  LANGFUSE_BASE_URL=http://localhost:3000"


langfuse-down:
	docker compose -p mewhelp-langfuse -f docker-compose.langfuse.yml down


cost-report:  ## ch09 按意图 token 账(需 Langfuse 在跑;DAYS=窗口天数)
	PYTHONPATH=. uv run python scripts/cost_by_intent.py --days $(or $(DAYS),7)


flywheel:  ## ch09 飞轮批处理:问题池 → 标准化查重 → 待审队列(需 mysql + 聊天上游)
	PYTHONPATH=. uv run python scripts/flywheel_pipeline.py


flywheel-samples:  ## ch09 标准化查重 prompt 标注样例验证(通过率 ≥ 80%)
	PYTHONPATH=. uv run python scripts/validate_flywheel_samples.py


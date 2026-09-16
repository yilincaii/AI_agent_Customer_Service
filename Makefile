export PYTHONUTF8 = 1
.PHONY: dev test
dev:
	uv run uvicorn app.main:app --port 8000
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

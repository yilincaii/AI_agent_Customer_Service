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

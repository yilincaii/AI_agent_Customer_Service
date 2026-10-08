# MeowDesk

I built MeowDesk as a customer service assistant for an online store. It answers questions about products and store policies, looks up orders and delivery information, and guides users through refund requests or creating a support ticket. I wanted it to check stored information and call tools when needed, rather than answer everything from the model alone.

The application has a streaming chat interface and an admin interface for maintaining the knowledge base, reviewing unanswered questions, checking retrieval results, and tracking model usage. Conversations are saved, and users can resume a request after confirming an action.

## Stack

| Part | What I use |
|---|---|
| Backend | Python 3.12+, FastAPI, Uvicorn |
| Agent workflow | LangGraph, LangChain, MCP |
| Storage | MySQL with SQLAlchemy; SQLite for workflow checkpoints |
| Search | Milvus Standalone, vector search, BM25, reranking |
| Models | An OpenAI-compatible chat API; embedding and reranking APIs |
| Interface | HTML, CSS, JavaScript |
| Optional tools | Langfuse for tracing; PyTorch, Transformers and ONNX for topic classification |
| Development | uv, Docker Compose, pytest |

The default embedding model is `BAAI/bge-m3`, and the default reranker is `BAAI/bge-reranker-v2-m3`. Their API addresses default to SiliconFlow. The reranking endpoint uses a separate `/rerank` interface; an OpenAI-compatible chat endpoint alone is not enough.

## Run locally

Use macOS or Linux with Python 3.12+, uv, Docker Compose, Bash and make. On Windows, use WSL2. Docker needs to be running before starting the application.

From the repository root:

```bash
uv sync --python 3.12
cp .env.example .env
```

Edit `.env` and replace the placeholders. The required model settings are:

```dotenv
CHAT_BASE_URL=your-chat-api-base-url
CHAT_MODEL=your-provider-model-name
CHAT_API_KEY=your-chat-api-key
EMBED_API_KEY=your-embedding-api-key
RERANK_API_KEY=your-reranking-api-key
```

Use a chat model that supports tool calling and structured output. Check the model-specific thinking settings in `.env.example`; they should match the provider you choose. If the model is not covered by the built-in context budget settings, set `MODEL_CONTEXT_WINDOW` to its documented token limit.

Set `DATABASE_URL` explicitly. For the unchanged local Docker configuration, these development values match the bundled MySQL container:

```dotenv
DATABASE_URL=mysql+asyncmy://root:root@127.0.0.1:3306/mewhelp
TEST_DATABASE_URL=mysql+asyncmy://root:root@127.0.0.1:3306/mewhelp_test
```

These are local development credentials. Keep `.env` out of Git. Intent recognition and conversation summaries use the chat model by default; separate `INTENT_*` and `SUMMARY_*` settings are optional. Langfuse is also optional.

Start the database and search services:

```bash
docker compose up -d
docker compose ps
```

Wait for the services to become healthy. MySQL runs the files in `sql/` when its data volume is first created; restarting an existing volume does not rerun those files.

Build and vectorize the bundled knowledge documents:

```bash
make kb-build
make kb-vectorize
```

Vectorization needs a working embedding API. Then start the application:

```bash
make dev
```

This checks the Docker services, starts the two local MCP servers, and runs FastAPI. Open:

```text
http://localhost:8000
```

The admin interface is at `/admin`, and the API documentation is at `/docs`.

For deployment, I would start with a single application process on a Linux host and persistent database volumes. The repository does not include a complete production deployment configuration. Before exposing it publicly, add authentication, HTTPS and restricted access to the database, search service and admin endpoints.

## Directories

```text
app/          API routes, agent workflow, retrieval, database access and web pages
mcp_servers/  Local logistics and after-sales tool servers
data/         Knowledge documents, classification data and generated runtime files
scripts/      Knowledge ingestion, evaluation, calibration and model utilities
sql/          Database schema and seed data
tests/        Unit, API and integration tests
docs/         Design and implementation notes
primer/       Small standalone integration prototypes
```

## Tests

With `.env` configured and MySQL and Milvus running:

```bash
uv run pytest -q
```

Use a separate database in `TEST_DATABASE_URL`. The database fixtures create it if needed and drop and recreate its tables. The full suite includes service integration tests, so it needs more than Python dependencies alone.

Topic model training and export use the optional dependency group:

```bash
uv sync --group ml
```

The classifier also needs trained or exported model files. Those files are not included in the repository and are not required for the basic chat application.

## Data and limits

I use bundled Chinese customer support text for classification experiments: a 34-record internal dataset and a 2,916-record external dataset. The external dataset’s upstream source and license are not documented here.

Order, product and logistics tools currently use mock data rather than a live store connection. The assistant can still misunderstand a request or retrieve weak evidence, so uncertain answers and consequential actions need review. Model calls depend on external services and may incur charges.

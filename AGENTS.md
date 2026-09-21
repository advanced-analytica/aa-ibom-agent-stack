# AGENTS.md

This file provides guidance for AI coding agents (Codex, Copilot, Cursor, Zed, OpenCode).

## Project Overview

**ibom_ai_agent_stack** - FastAPI application generated with [Full-Stack AI Agent Template](https://github.com/vstorm-co/full-stack-ai-agent-template).

**Stack:** FastAPI + Pydantic v2, PostgreSQL
, JWT + API Key auth, Redis
, pydantic_ai (google), RAG (pgvector), Next.js 15 (i18n)

## Commands

```bash
# Run server
cd backend && uv run uvicorn app.main:app --reload

# Tests & lint
pytest
ruff check . --fix && ruff format .

# Migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "Description"

# RAG
uv run ibom_ai_agent_stack rag-ingest /path/to/file.pdf --collection docs
uv run ibom_ai_agent_stack rag-search "query" --collection docs

# Sync Sources
uv run ibom_ai_agent_stack cmd rag-sources
uv run ibom_ai_agent_stack cmd rag-source-add
uv run ibom_ai_agent_stack cmd rag-source-sync
```

## Project Structure

```
backend/app/
├── api/routes/v1/    # Endpoints
├── services/         # Business logic
├── repositories/     # Data access
├── schemas/          # Pydantic models
├── db/models/        # DB models
├── agents/           # AI agents
├── rag/              # RAG (embeddings, vector store, ingestion)
│   └── connectors/   # Sync source connectors
└── commands/         # CLI commands
```

## Key Conventions

- `db.flush()` in repositories, not `commit()`
- Services raise `NotFoundError`, `AlreadyExistsError`
- Separate `Create`, `Update`, `Response` schemas
- Commands auto-discovered from `app/commands/`
- Document ingestion via CLI and API upload
- Sync sources: configurable connectors with scheduled sync

## Agent Tooling

- Canonical skill definitions live under `.agents/skills`, following the agent skills dot io protocol as the shared, tool-agnostic source of truth.
- `.claude/skills` is a symlink to `.agents/skills`; do not replace it with copied files or add a sync script.
- Commands are tool-specific and stay separate. Claude commands in `.claude/commands` and Codex custom prompts are not the same format and must not be symlinked or merged.
- Future agent tooling should use the same pattern: shared skills under `.agents/skills`, tool-local commands in that tool's own command/prompt folder.

## More Info

- `docs/architecture.md` - Architecture details
- `docs/adding_features.md` - How to add features
- `docs/testing.md` - Testing guide
- `docs/patterns.md` - Code patterns

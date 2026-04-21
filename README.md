# Interviewer Agent Skeleton

An extensible **FastAPI + SQLAlchemy + LLM provider adapter** skeleton for building an interview simulation backend.

## Current Scope

- Layered application structure that is easy to extend
- Three core entities: `Interview`, `Turn`, and `Report`
- Provider adapter layer for `mock`, `gemini`, and `openai`
- Local development flow that works with `mock` and no API key
- SQLite by default, with room to move to PostgreSQL later
- API routes for the core interview lifecycle

## Project Structure

```text
app/
  api/
    deps.py
    router.py
    routes/
      health.py
      interviews.py
      reports.py
  core/
    config.py
    lifespan.py
    logging.py
  db/
    base.py
    session.py
    models/
      interview.py
      report.py
      turn.py
  domain/
    schemas/
      interview.py
      report.py
      turn.py
    services/
      interview_service.py
      report_service.py
      scoring_service.py
  infra/
    llm/
      base.py
      gemini_provider.py
      mock_provider.py
      openai_provider.py
      registry.py
    repositories/
      interview_repo.py
      report_repo.py
      turn_repo.py
  prompts/
    grading_system.txt
    interviewer_system.txt
  main.py
tests/
  test_health.py
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Copy environment variables

```bash
cp .env.example .env
```

On Windows, copy the file manually and rename it to `.env`.

### 3. Start the server

```bash
uvicorn app.main:app --reload
```

Available endpoints:

- `GET /health`
- `POST /api/interviews`
- `POST /api/interviews/{id}/reply`
- `POST /api/interviews/{id}/finish`
- `GET /api/interviews/{id}`
- `GET /api/interviews/{id}/report`

## Default Runtime Settings

`.env.example` defaults to:

- `LLM_PROVIDER=mock`
- `DATABASE_URL=sqlite:///./app.db`

That means you can run the full API flow locally without a real LLM provider.

## Switch To Gemini

1. Install the dependencies in `requirements.txt`
2. Set `LLM_PROVIDER=gemini`
3. Set `GEMINI_API_KEY=your-key`
4. Restart the server

## Switch To OpenAI

1. Set `LLM_PROVIDER=openai`
2. Set `OPENAI_API_KEY=your-key`
3. Restart the server

## Suggested Next Steps

1. Add PostgreSQL and Alembic migrations
2. Add authentication and user ownership
3. Add resume upload and resume parsing
4. Version prompts and evaluation rubrics
5. Add interview history and report browsing

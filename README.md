# financial-advisor-service

FastAPI boilerplate.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
```

## Run

```bash
make run            # or: .venv/bin/uvicorn app.main:app --reload
```

Docs at http://localhost:8000/docs, health at http://localhost:8000/api/v1/health.

## Test / lint

```bash
make test
make lint
```

## Layout

```
app/
  main.py            # app factory + lifespan
  core/              # settings, logging, exception handlers
  api/
    deps.py          # shared dependencies
    v1/
      router.py      # aggregates v1 routes
      routes/        # one module per resource
  schemas/           # pydantic request/response models
  services/          # business logic (keep routes thin)
tests/
```

Add a feature: create `app/api/v1/routes/<name>.py`, define schemas in `app/schemas/`,
put logic in `app/services/`, and register the router in `app/api/v1/router.py`.

## Run with Docker

Prerequisites: the `datakern-engineering-foundation` compose project (Postgres)
is running, and `.env` exists with the `DB_*` and `GROQ_API_KEY` values.

```bash
make up      # builds the image, starts app + Phoenix
make logs    # follow app logs
make down
```

- API docs: http://localhost:8000/docs
- Phoenix traces: http://localhost:6006

The compose file joins the Postgres project's network and overrides `DB_HOST`
to `postgres`, and points the app at the Phoenix container. Your `.env` keeps
`DB_HOST=localhost` for running on the host.

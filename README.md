# Project 4 – Software Quality Analysis & Repair Using LLMs

**Group 17** · DevOps and Cloud-based Software · UvA MSc SE

A web application that analyses source code using static analysis tools
(Bandit, Ruff, Radon, TruffleHog) and uses Large Language Models to
automatically repair identified issues.

## Quick Start

```bash
# 1. Copy env file
cp .env.example .env

# 2. Run with Docker
docker compose up --build

# 3. Open http://localhost:8000/health
```

## Run Locally (without Docker)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Project Structure

```
app/
├── main.py              # FastAPI entry point + route wiring
├── domain/              # Pure domain objects (no framework deps)
│   ├── models.py        # Finding, Patch, Summary dataclasses
│   └── schemas.py       # Pydantic request/response schemas
├── core/                # Cross-cutting infrastructure
│   ├── config.py        # Settings from environment variables
│   ├── security.py      # Safe zip/tar extraction
│   └── util.py          # CLI runner, tool detection
├── analyzers/           # Static analysis tool adapters
├── normalizers/         # Raw output → unified Finding
├── services/            # Orchestration layer
├── repair/              # LLM repair strategies
├── llm/                 # LLM client wrappers
└── ui/                  # Minimal HTML + JS frontend
```

## API Endpoints

| Method | Endpoint               | Description            |
|--------|------------------------|------------------------|
| GET    | `/health`              | Health check           |

_More endpoints added per feature branch._

## Team

| Name               | Role                      |
|--------------------|---------------------------|
| Gerard García      | Product Owner  + DevOps   |
| Mohssin Assaban    | Scrum Master + DevOps     |
| Hidde Makimei      | Backend + Testing         |
| Oriol Fernandez    | Backend + QA + Monitoring |

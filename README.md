# Project 4 – Software Quality Analysis & Repair Using LLMs

**Group 17** · DevOps and Cloud-based Software · UvA MSc SE 2025

> A web application that analyses source code using four static analysis tools and uses Large Language Models to automatically repair identified issues.

Users upload a ZIP file or provide a GitHub URL, select which files to analyse, and receive a unified findings report covering security vulnerabilities, code smells, cyclomatic complexity, and leaked secrets — all in a single request. An LLM-powered repair pipeline generates patches to fix the reported issues automatically.

---

## Table of Contents

- [Deployment (AWS ECS Fargate)](#deployment-aws-ecs-fargate)
- [Run Locally (Docker Compose)](#run-locally-docker-compose)
- [Run Locally (without Docker)](#run-locally-without-docker)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [CI/CD](#cicd)
- [Configuration](#configuration)
- [Sprint Roadmap](#sprint-roadmap)
- [Team](#team)

---

## Deployment (AWS ECS Fargate)

The application is deployed on **AWS ECS Fargate** — a serverless container platform that runs the Docker image without requiring you to manage EC2 instances. The service is accessible via a public DNS endpoint.

### Infrastructure Overview

```
Internet
    │
    ▼
Public DNS / IP
    │
    ▼
┌────────────────────────────────────┐
│         AWS ECS Fargate            │
│                                    │
│  ┌──────────────────────────────┐  │
│  │     ECS Task (container)     │  │
│  │                              │  │
│  │  ┌──────────┐  ┌──────────┐  │  │
│  │  │  nginx   │  │ FastAPI  │  │  │
│  │  │  :80     │─▶│  :8000   │  │  │
│  │  └──────────┘  └──────────┘  │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
```

### Accessing the Live Application

Once the ECS service is running, the application is available at the public IP or DNS name assigned to the Fargate task. Check the AWS ECS console under **Clusters → Tasks → Network** for the public IP, or the assigned DNS hostname.

- **Web UI:** `http://<public-dns-or-ip>/`
- **Swagger docs:** `http://<public-dns-or-ip>/docs`
- **Health check:** `http://<public-dns-or-ip>/health`

### Deploying to ECS Fargate

> **Note:** Automated CD (continuous deployment from GitHub Actions to ECS) is planned for Sprint 3. For now, deployment is done manually.

#### Prerequisites

- AWS CLI installed and configured (`aws configure`)
- Docker installed locally
- An ECR repository created for the image (or an alternative registry)
- An ECS cluster and task definition set up in your AWS account

#### Steps

```bash
# 1. Build the Docker image
docker build -t uva-qa-llm-mvp .

# 2. Authenticate Docker to ECR (replace with your account ID and region)
aws ecr get-login-password --region <region> | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com

# 3. Tag the image for ECR
docker tag uva-qa-llm-mvp:latest \
  <account-id>.dkr.ecr.<region>.amazonaws.com/uva-qa-llm-mvp:latest

# 4. Push to ECR
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/uva-qa-llm-mvp:latest

# 5. Update the ECS service to pull the new image
aws ecs update-service \
  --cluster <cluster-name> \
  --service <service-name> \
  --force-new-deployment
```

#### ECS Task Definition — Key Settings

| Setting | Value |
|---|---|
| Launch type | Fargate |
| CPU | 512 (0.5 vCPU) or higher |
| Memory | 1024 MB or higher |
| Network mode | `awsvpc` |
| Container port | 80 (nginx front) |
| Health check | `GET /health` |

#### Required Environment Variables (ECS Task Definition)

Set these as **environment variables** or **Secrets Manager** references in your task definition (never hardcode them):

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (required for LLM repair) |
| `DATA_DIR` | Session data directory (default: `data`) |
| `OPENAI_MODEL` | LLM model (default: `gpt-4o-mini`) |
| `LOG_LEVEL` | Logging verbosity (default: `INFO`) |

---

## Run Locally (Docker Compose)

For local development, Docker Compose is the fastest way to run the full stack (FastAPI backend + nginx reverse proxy).

```bash
# 1. Clone the repository
git clone https://github.com/ChiefGitau/UvA-DevOps-Software-QA-LLM-MVP.git
cd UvA-DevOps-Software-QA-LLM-MVP

# 2. (Optional) Create a .env for secrets
cp .env.example .env

# 3. Build and run
docker compose up --build

# 4. Open the UI
open http://localhost
```

Two containers will start:

| Container | Image | Port | Role |
|---|---|---|---|
| `p4-backend` | Custom (Python 3.11-slim) | 8000 (internal) | FastAPI app + analysis tools |
| `p4-nginx` | nginx:1.27-alpine | 80 (external) | Reverse proxy, upload buffering |

nginx waits for the backend health check to pass before accepting traffic.

---

## Run Locally (without Docker)

Requires Python 3.11+ and the analysis tools installed on your system.

```bash
# Create virtual environment
python -m venv venv && source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install analysis tools if not using Docker
pip install bandit ruff radon
# TruffleHog: https://github.com/trufflesecurity/trufflehog/releases

# Start the server
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` in your browser.

---

## Usage

### Web UI

1. **Upload** a `.zip` file containing Python source code, or **clone** a public GitHub repository by pasting its URL.
2. **Select files** to include in the analysis using the checkbox list.
3. Click **Run Analysis** — all four tools execute and results appear in a sortable findings table.

### cURL Examples

```bash
# Upload a ZIP
curl -X POST http://<host>/api/session/upload \
  -F "archive=@code.zip"
# → {"session_id": "abc-123-..."}

# Or clone from GitHub
curl -X POST http://<host>/api/session/clone \
  -H "Content-Type: application/json" \
  -d '{"git_url": "https://github.com/owner/repo"}'

# List extracted files
curl http://<host>/api/session/{session_id}/files

# Run analysis on all files with all tools
curl -X POST http://<host>/api/analyse \
  -H "Content-Type: application/json" \
  -d '{"session_id": "{session_id}"}'

# Retrieve the persisted report
curl http://<host>/api/session/{session_id}/report
```

Replace `<host>` with `localhost` for local runs, or the ECS public DNS/IP for the live deployment.

### Interactive API Docs

FastAPI provides auto-generated documentation at:

- **Swagger UI:** `http://<host>/docs`
- **ReDoc:** Coming soon

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Minimal web UI |
| `GET` | `/health` | Health check (`{"status": "healthy"}`) |
| `POST` | `/api/session/upload` | Upload a ZIP archive, returns `session_id` |
| `POST` | `/api/session/clone` | Clone a GitHub repo, returns `session_id` |
| `GET` | `/api/session/{id}` | Session info (source type, config) |
| `GET` | `/api/session/{id}/files` | List files in workspace |
| `GET` | `/api/analyzers` | List available tools (`["bandit","radon","ruff","trufflehog"]`) |
| `POST` | `/api/analyse` | Run analysis, returns unified findings + summary |
| `GET` | `/api/session/{id}/report` | Retrieve persisted findings JSON |

---

## Architecture

### Current (Sprint 1–2) — Analysis Pipeline

```
┌─────────┐     ┌───────┐     ┌──────────────────────────────────┐
│ Browser │────▶│ nginx │────▶│          FastAPI Backend         │
│  (UI)   │◀────│  :80  │◀────│             :8000                │
└─────────┘     └───────┘     │                                  │
                              │  ┌─────────────────────────────┐ │
               Upload ZIP     │  │     Session Service         │ │
               or Git URL     │  │  (workspace management)     │ │
                   │          │  └──────────┬──────────────────┘ │
                   ▼          │             │                    │
              ┌──────────┐    │  ┌──────────▼──────────────────┐ │
              │workspace │    │  │    Analysis Service         │ │
              │ raw → sel│    │  │  (orchestration)            │ │
              └──────────┘    │  └──┬────┬────┬────┬───────────┘ │
                              │     │    │    │    │             │
                              │  ┌──▼┐┌──▼┐┌─▼─┐┌─▼───────────┐  │
                              │  │Ban││Ruf││Rad││TruffleHog   │  │
                              │  │dit││ f ││on ││  (binary)   │  │
                              │  └──┬┘└──┬┘└─┬─┘└─┬───────────┘  │
                              │     │    │   │    │ raw output   │
                              │  ┌──▼────▼───▼────▼────────────┐ │
                              │  │    Normalizer Registry      │ │
                              │  │  → Unified Finding objects  │ │
                              │  └──────────┬──────────────────┘ │
                              │             ▼                    │
                              │     findings_unified.json        │
                              └──────────────────────────────────┘
```

### AWS Deployment Architecture (Current)

```
Internet ──▶ Public DNS/IP ──▶ ECS Fargate Task
                                      │
                          ┌───────────▼──────────────┐
                          │   Docker Container       │
                          │  nginx :80 ──▶ app :8000 │
                          └──────────────────────────┘
```

### Planned (Sprint 3–4) — Full Cloud Pipeline

```
GitHub Push
    │
    ▼
GitHub Actions CI (lint + test)
    │ (on merge to main)
    ▼
Build & Push image ──▶ Amazon ECR
    │
    ▼
Deploy ──▶ ECS Fargate (force new deployment)
    │
    ▼
CloudWatch Metrics Dashboard
```

### Design Patterns

- **Registry + Strategy** — Analyzers and normalizers are registered by name; new tools are added by implementing one class and registering it in `containers.py`.
- **Session-based workspace** — Each analysis runs in an isolated directory (`data/{session_id}/`), keeping concurrent sessions safe.
- **Two-phase file selection** — Files are first extracted into `workspace_raw`, then user-selected files are copied to `workspace` (the active directory tools run against).

---

## Project Structure

```
.
├── app/
│   ├── main.py                  # FastAPI entry point, route wiring, health check
│   ├── api/
│   │   ├── session_routes.py    # Upload, clone, file listing endpoints
│   │   └── analysis_routes.py   # Analyse, report, analyzer listing endpoints
│   ├── domain/
│   │   ├── models.py            # Finding, Patch, Summary, Report dataclasses
│   │   └── schemas.py           # Pydantic request/response schemas
│   ├── core/
│   │   ├── config.py            # Settings from environment variables
│   │   ├── containers.py        # Dependency injection (registry builders)
│   │   ├── security.py          # Safe zip/tar extraction
│   │   └── util.py              # CLI runner helper
│   ├── analyzers/               # Static analysis tool adapters
│   │   ├── base.py              # StaticCodeAnalyzer ABC + RawToolResult
│   │   ├── registry.py          # AnalyzerRegistry (pick, list, get)
│   │   ├── bandit.py            # Security scanner
│   │   ├── ruff.py              # Linter / code smell detector
│   │   ├── radon.py             # Cyclomatic complexity analyser
│   │   └── trufflehog.py        # Secrets detector
│   ├── normalizers/             # Raw tool output → unified Finding
│   │   ├── base.py              # ToolNormalizer ABC + NormalizationContext
│   │   ├── registry.py          # NormalizerRegistry
│   │   ├── bandit_normalizer.py
│   │   ├── ruff_normalizer.py
│   │   ├── radon_normalizer.py
│   │   ├── trufflehog_normalizer.py
│   │   └── util.py              # Snippet extraction, path normalisation
│   ├── services/
│   │   ├── session_service.py   # Workspace directory management
│   │   ├── repo_service.py      # Git clone (shallow, HTTPS)
│   │   ├── selection_service.py # workspace_raw → workspace file copy
│   │   └── analysis_service.py  # Orchestrates analyse + normalise
│   ├── repair/                  # LLM repair strategies
│   ├── llm/                     # LLM client wrappers
│   └── ui/
│       ├── templates/index.html # Minimal single-page UI
│       └── static/              # CSS + JS assets
├── tests/                       # 48 pytest tests
├── demo/
│   └── domain.py                # Intentionally buggy file for testing
├── nginx/
│   └── default.conf             # Reverse proxy configuration
├── Dockerfile                   # Python 3.11 + tools + TruffleHog binary
├── docker-compose.yml           # Local dev: backend + nginx orchestration
├── .github/workflows/ci.yml    # Lint + test CI pipeline
├── .env.example                 # Environment variable template
├── requirements.txt             # Runtime dependencies
├── requirements-test.txt        # Test dependencies
├── pyproject.toml               # Package config + ruff settings
└── pytest.ini                   # Test configuration
```

---

## Testing

The project uses **pytest** with 48 tests covering all layers.

```bash
# Install test dependencies
pip install -r requirements-test.txt
pip install -e .

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_analysis_ui.py -v
```

### Test Breakdown

| Test File | Count | Covers |
|---|---|---|
| `test_health.py` | 2 | Health endpoint |
| `test_session_upload.py` | 7 | Upload, clone, file listing, session info |
| `test_analysis_ui.py` | 12 | Full analysis pipeline, unified report, UI serving |
| `test_bandit_analyzer.py` | 2 | Bandit tool execution (mock + missing tool) |
| `test_bandit_normalizer.py` | 1 | Bandit JSON → Finding normalisation |
| `test_ruff_analyzer.py` | 2 | Ruff tool execution |
| `test_ruff_normalizer.py` | 1 | Ruff JSON → Finding normalisation |
| `test_radon_analyzer.py` | 2 | Radon tool execution |
| `test_radon_normalizer.py` | 1 | Radon JSON → Finding normalisation |
| `test_trufflehog_analyzer.py` | 2 | TruffleHog tool execution |
| `test_trufflehog_normalizer.py` | 5 | TruffleHog JSONL parsing, severity, redaction |
| `test_path_utils.py` | 5 | Path normalisation (absolute, relative, container) |
| `test_docker_compose.py` | 5 | Compose structure, healthchecks, nginx dependency |
| `test_secrets.py` | 6 | No hardcoded secrets, env file integrity |

All tests run without Docker or external services — analyzers are mocked where needed.

---

## CI/CD

### CI Pipeline (GitHub Actions)

Every push and pull request to `development` or `main` triggers the CI workflow (`.github/workflows/ci.yml`):

```
Push / PR
    │
    ▼
┌─────────────┐     ┌──────────────────────┐
│  Lint (Ruff) │────▶│   Test (Pytest)       │
│  check +     │     │  --cov, fail < 50%   │
│  format      │     └──────────────────────┘
└─────────────┘
```

- **Lint job** — `ruff check` + `ruff format --check` on `app/` and `tests/`
- **Test job** — Runs after lint passes; `pytest --cov=app` with a minimum 50% coverage gate
- Python 3.11, pip cache enabled for fast runs

### CD Pipeline (Planned — Sprint 3)

Automated deployment to ECS Fargate on merge to `main` is planned for Sprint 3:

```
Merge to main
    │
    ▼
CI passes (lint + test)
    │
    ▼
Build & push Docker image to ECR
    │
    ▼
aws ecs update-service --force-new-deployment
```

### Branching Strategy

```
main ◀── development ◀── feature/QALLM-{id}/{description}
```

- Feature branches off `development`, one branch per Jira story
- PR reviews required before merge
- CI must pass before merge

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` for local use, or set these in your ECS task definition for the live deployment:

| Variable | Default | Description |
|---|---|---|
| `DATA_DIR` | `data` | Directory for session data storage |
| `OPENAI_API_KEY` | *(empty)* | OpenAI API key (required for LLM repair) |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM model for code repair |
| `TOKEN_BUDGET` | `20000` | Max tokens per repair session |
| `MAX_REPAIR_ISSUES` | `10` | Max findings to repair per run |
| `STORAGE_BACKEND` | `local` | Storage backend (local only for PoC) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

> **Important:** Secrets are **never hardcoded** — enforced by CI tests that scan `app/` for credential patterns. On AWS, use ECS task definition environment variables or AWS Secrets Manager.

---

## Sprint Roadmap

### ✅ Sprint 1 — Foundation (Weeks 2–3)

| ID | Story | Status |
|---|---|---|
| QALLM-17 | Dockerised backend API | ✅ Done |
| QALLM-1 | Upload code (ZIP) | ✅ Done |
| QALLM-6 | GitHub repository clone | ✅ Done |
| QALLM-7 | Bandit security scanning | ✅ Done |
| QALLM-8 | Ruff code smell detection | ✅ Done |
| QALLM-9 | Radon complexity analysis | ✅ Done |
| QALLM-10 | TruffleHog secrets detection | ✅ Done |
| QALLM-11 | Unified findings report | ✅ Done |
| QALLM-15 | Minimal web UI | ✅ Done |
| QALLM-16 | CI pipeline (lint + test) | ✅ Done |
| QALLM-18 | Docker Compose + nginx | ✅ Done |
| QALLM-19 | Secrets via env vars | ✅ Done |

### 🔜 Sprint 2 — LLM Repair (Weeks 3–4)

| ID | Story |
|---|---|
| QALLM-2 | LLM repair for findings |
| QALLM-3 | Verification (re-run tools after repair) |
| QALLM-4 | Downloadable patched code |
| QALLM-5 | Cost tracking (token budget) |
| QALLM-20 | Enhanced UI (results dashboard) |
| QALLM-21 | Docker image publishing to ECR |
| QALLM-22 | Infrastructure-as-Code (CloudFormation) |

### 🔜 Sprint 3 — Deployment & Monitoring (Weeks 5–6)

| ID | Story |
|---|---|
| QALLM-23 | CD pipeline (auto-deploy to ECS on merge) |
| QALLM-24 | AWS ECS Fargate deployment ✅ In progress |
| QALLM-25 | Integration test suite |
| QALLM-26 | Prometheus + Grafana metrics |

### 🔜 Sprint 4 — Observability (Week 7)

| ID | Story |
|---|---|
| QALLM-27 | CloudWatch dashboard |

---

## Adding a New Analysis Tool

The registry/strategy architecture makes it straightforward to add new tools:

1. **Analyzer** — Create `app/analyzers/mytool.py`, implement `StaticCodeAnalyzer` (two methods: `tool_name()` and `analyze()`).
2. **Normalizer** — Create `app/normalizers/mytool_normalizer.py`, implement `ToolNormalizer` (set `tool_name` and implement `normalize()`).
3. **Register** — Add both to `app/core/containers.py`.
4. **Test** — Add analyzer + normalizer tests following existing patterns.
5. **Dockerfile** — Install the tool binary/package in the Dockerfile.

The new tool will automatically appear in `/api/analyzers` and run during analysis.

---

## Team

| Name | Role | GitHub |
|---|---|---|
| Gerard García | Product Owner + DevOps | |
| Mohssin Assaban | Scrum Master + DevOps | [@assaban](https://github.com/assaban) |
| Hidde Makimei | Backend + Testing | |
| Oriol Fernandez | Backend + QA + Monitoring | |

**Customer:** Dr. Nafis Islam (UvA)

---

## License

University of Amsterdam (MSc. Software Engineering 2526 DevOps coursework). Not licensed for redistribution.

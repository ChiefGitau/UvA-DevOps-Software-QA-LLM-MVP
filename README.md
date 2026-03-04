# Project 4 – Software Quality Analysis & Repair Using LLMs

**Group 17** · DevOps and Cloud-based Software · UvA MSc SE 2025

> A web application that analyses source code using four static analysis tools and uses Large Language Models to automatically repair identified issues.

Users upload a ZIP file or provide a GitHub URL, select which files to analyse, and receive a unified findings report covering security vulnerabilities, code smells, cyclomatic complexity, and leaked secrets, all in a single request. The LLM-powered repair engine then generates targeted patches to fix reported issues, with support for multiple models (OpenAI GPT-4o-mini/GPT-5-mini, Anthropic Claude, and local Ollama) selectable per-request.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Run Locally (without Docker)](#run-locally-without-docker)
- [Usage](#usage)
- [LLM Configuration](#llm-configuration)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [CI/CD](#cicd)
- [Configuration](#configuration)
- [Adding a New Analysis Tool](#adding-a-new-analysis-tool)
- [Adding a New LLM Model](#adding-a-new-llm-model)
- [Sprint Roadmap](#sprint-roadmap)
- [Team](#team)

---

## Quick Start

The fastest way to run the application is with Docker Compose, which starts both the FastAPI backend and an nginx reverse proxy.

```bash
# 1. Clone the repository
git clone https://github.com/ChiefGitau/UvA-DevOps-Software-QA-LLM-MVP.git
cd UvA-DevOps-Software-QA-LLM-MVP

# 2. Create a .env with your API keys
cp .env.example .env
# Edit .env and add at least OPENAI_API_KEY

# 3. Build and run
docker compose up --build

# 4. Open the UI
open http://localhost
```

Two containers will start:

| Container | Image | Port | Role |
|-----------|-------|------|------|
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

# (Optional) Install analysis tools if not using Docker
pip install bandit ruff radon
# TruffleHog: https://github.com/trufflesecurity/trufflehog/releases

# (Optional) Install LLM SDK for your provider(s)
pip install openai          # For GPT-4o-mini / GPT-5-mini
pip install anthropic       # For Claude 3.5 Haiku
pip install ollama          # For local Ollama models

# Start the server
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` in your browser.

---

## Usage

### Web UI

1. **Upload** a `.zip` file containing Python source code, or **clone** a public GitHub repository by pasting its URL.
2. **Select files** to include in the analysis using the checkbox list.
3. Click **Run Analysis**: all four tools execute and results appear in a sortable findings table.
4. **Repair**: select an LLM model from the dropdown (or leave on "Auto" for severity-based routing) and click **Repair Findings**. Patches are generated, applied, and shown with expandable unified diffs.

### cURL Examples

```bash
# Upload a ZIP
curl -X POST http://localhost/api/session/upload \
  -F "archive=@code.zip"
# → {"session_id": "abc-123-..."}

# Or clone from GitHub
curl -X POST http://localhost/api/session/clone \
  -H "Content-Type: application/json" \
  -d '{"git_url": "https://github.com/owner/repo"}'

# List extracted files
curl http://localhost/api/session/{session_id}/files

# Run analysis
curl -X POST http://localhost/api/analyse \
  -H "Content-Type: application/json" \
  -d '{"session_id": "{session_id}"}'

# Check available LLM models
curl http://localhost/api/llm/providers
# → {"available":["gpt-4o-mini","gpt-5-mini","claude-3-5-haiku-20241022","ollama/llama3.1:8b"],
#    "configured":["gpt-4o-mini","gpt-5-mini"],"default":"gpt-4o-mini"}

# Repair with auto model routing (strong for HIGH/CRITICAL, fast for MEDIUM/LOW)
curl -X POST http://localhost/api/repair/{session_id}

# Repair with a specific model
curl -X POST http://localhost/api/repair/{session_id} \
  -H "Content-Type: application/json" \
  -d '{"provider": "gpt-5-mini"}'

# Get repair report
curl http://localhost/api/repair/{session_id}/report
```

### Interactive API Docs

FastAPI provides auto-generated documentation at:
- **Swagger UI:** `http://localhost/docs`
- **ReDoc:** `http://localhost/redoc`

---

## LLM Configuration

### Supported Models

| Model | Provider | Type | Notes |
|-------|----------|------|-------|
| `gpt-4o-mini` | OpenAI | Fast / cheap | Default for MEDIUM/LOW findings |
| `gpt-5-mini` | OpenAI | Strong | Default for HIGH/CRITICAL; uses structured outputs |
| `claude-3-5-haiku-20241022` | Anthropic | Fast | Good code understanding |
| `ollama/llama3.1:8b` | Ollama | Local / free | No API key needed, runs on your machine |

### Quick Setup

```bash
# In your .env file:

# OpenAI (enables gpt-4o-mini and gpt-5-mini)
OPENAI_API_KEY=sk-...

# Anthropic (enables claude-3-5-haiku)
ANTHROPIC_API_KEY=sk-ant-...

# Ollama (local, install from https://ollama.com)
# Then: ollama pull llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
```

### Auto Model Routing

When no model is explicitly selected ("Auto" in the UI, or no `provider` field in the API request), the system routes by finding severity:

- **CRITICAL / HIGH** → `LLM_STRONG_MODEL` (default: `gpt-5-mini`)
- **MEDIUM / LOW** → `LLM_FAST_MODEL` (default: `gpt-4o-mini`)

This keeps costs low while using the best model where it matters.

### Structured Outputs

GPT-5-mini uses OpenAI's JSON schema structured outputs, the LLM returns `{"corrected_code": "..."}` instead of raw text, eliminating fragile markdown fence stripping.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Minimal web UI |
| `GET` | `/health` | Health check (status, tools, uptime) |
| `POST` | `/api/session/upload` | Upload a ZIP archive, returns `session_id` |
| `POST` | `/api/session/clone` | Clone a GitHub repo, returns `session_id` |
| `GET` | `/api/session/{id}` | Session info (source type, config) |
| `GET` | `/api/session/{id}/files` | List files in workspace |
| `GET` | `/api/analyzers` | List available tools |
| `POST` | `/api/analyse` | Run analysis, returns unified findings + summary |
| `GET` | `/api/session/{id}/report` | Retrieve persisted findings JSON |
| `GET` | `/api/llm/providers` | List available/configured LLM models |
| `POST` | `/api/repair/{id}` | Run LLM repair (optional: `provider`, `max_issues`, `finding_ids`) |
| `GET` | `/api/repair/{id}/report` | Retrieve persisted repair report |

---

## Architecture

### Full Pipeline

```
  Upload/Clone ──▶ Analyse ──▶ LLM Repair ──▶ Report
                     │              │
              ┌──────▼──────┐  ┌───▼──────────────────────────┐
              │  4 Analyzers │  │     LLM Model Registry       │
              │  (registry)  │  │  ┌──────────┐ ┌───────────┐  │
              └──────────────┘  │  │gpt-4o-   │ │gpt-5-mini │  │
                                │  │  mini    │ │(structured)│  │
                                │  └──────────┘ └───────────┘  │
                                │  ┌──────────┐ ┌───────────┐  │
                                │  │ claude-  │ │ ollama/   │  │
                                │  │ 3-5-haiku│ │ llama3    │  │
                                │  └──────────┘ └───────────┘  │
                                └──────────────────────────────┘
```

### LLM Model Registry

Each dropdown entry is one `LLMModel` instance with its own API logic. The registry mirrors the analyzer registry pattern, one class per model, one `register()` call.

```
┌──────────────────────────────────────────────────────┐
│                  LLMModelRegistry                    │
│  .register()  .pick()  .list_configured()            │
├──────────────┬──────────────┬────────────┬───────────┤
│ gpt-4o-mini  │ gpt-5-mini   │ claude-3-5 │ ollama/   │
│ (OpenAI,     │ (OpenAI,     │ -haiku     │ llama3    │
│  max_tokens) │  structured, │ (Anthropic)│ (local)   │
│              │  max_compl.) │            │           │
├──────────────┴──────────────┴────────────┴───────────┤
│                   LLMModel ABC                       │
│        name()  is_configured()  chat()               │
│        LLMResponse   TokenTracker                    │
└──────────────────────────────────────────────────────┘
```

### Repair Pipeline Detail

```
findings_unified.json
        ↓
  sort by severity → cap at MAX_REPAIR_ISSUES → skip SECRET type
        ↓
  ┌─ for each finding ────────────────────────────────┐
  │  route model (CRITICAL/HIGH → strong, else fast)  │
  │  extract AST function/class context + padding     │
  │  build targeted prompt (senior engineer persona)  │
  │  call LLM via registry                            │
  │  strip fences (fallback) or parse structured JSON │
  │  generate unified diff                            │
  │  apply patch via safe line-slicing                │
  └───────────────────────────────────────────────────┘
        ↓
  repair_report.json (patches + token_usage)
```

### Design Patterns

- **Registry + Strategy**: Analyzers, normalizers, and LLM models are all registered by name; new entries are added by implementing one class and registering in `containers.py`.
- **Session-based workspace**: Each analysis runs in an isolated directory (`data/{session_id}/`), keeping concurrent sessions safe.
- **Two-phase file selection**: Files are first extracted into `workspace_raw`, then user-selected files are copied to `workspace`.
- **Safe line-slicing**: Patches are applied by replacing specific line ranges, not string matching, preventing accidental mismatches from duplicate code.

---

## Project Structure

```
.
├── app/
│   ├── main.py                  # FastAPI entry point, route wiring, health check
│   ├── api/
│   │   ├── session_routes.py    # Upload, clone, file listing endpoints
│   │   ├── analysis_routes.py   # Analyse, report, analyzer listing endpoints
│   │   └── repair_routes.py     # LLM repair + model listing endpoints
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
│   ├── llm/                     # LLM model implementations
│   │   ├── base.py              # LLMModel ABC, LLMResponse, TokenTracker
│   │   ├── registry.py          # LLMModelRegistry (pick, list, list_configured)
│   │   ├── openai_provider.py   # OpenAIModel (gpt-4o-mini, gpt-5-mini)
│   │   ├── anthropic_provider.py# AnthropicModel (Claude 3.5 Haiku)
│   │   ├── ollama_provider.py   # OllamaModel (local, lazy import)
│   │   └── openai_client.py     # Backward-compatibility shim
│   ├── repair/                  # LLM repair pipeline
│   │   ├── context_extractor.py # AST-based function/class extraction
│   │   └── prompt_builder.py    # Senior engineer prompt + safe alternatives
│   ├── services/
│   │   ├── session_service.py   # Workspace directory management
│   │   ├── repo_service.py      # Git clone (shallow, HTTPS)
│   │   ├── selection_service.py # workspace_raw → workspace file copy
│   │   ├── analysis_service.py  # Orchestrates analyse + normalise
│   │   └── repair_service.py    # LLM repair orchestrator (routing, patching)
│   └── ui/
│       ├── templates/index.html # Single-page UI (4 steps)
│       └── static/              # CSS + JS assets
├── tests/                       # 103 pytest tests
├── demo/
│   └── domain.py                # Intentionally buggy file for testing
├── nginx/
│   └── default.conf             # Reverse proxy configuration
├── Dockerfile                   # Python 3.11 + tools + TruffleHog binary
├── docker-compose.yml           # backend + nginx orchestration
├── .github/workflows/ci.yml    # Lint + test CI pipeline
├── .env.example                 # Environment variable template
├── requirements.txt             # Runtime dependencies
├── requirements-test.txt        # Test dependencies
├── pyproject.toml               # Package config + ruff settings
└── pytest.ini                   # Test configuration
```

---

## Testing

The project uses **pytest** with 103 tests covering all layers.

```bash
# Install test dependencies
pip install -r requirements-test.txt
pip install -e .

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_repair_service.py -v
```

### Test Breakdown

| Test File | Count | Covers |
|-----------|-------|--------|
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
| `test_secrets.py` | 6 | No hardcoded secrets, env file integrity |
| `test_llm_registry.py` | 9 | Model registry: register, pick, list, API endpoint |
| `test_llm_client.py` | 11 | OpenAI models: gpt-4o vs gpt-5 params, structured outputs, shim |
| `test_anthropic_provider.py` | 6 | Anthropic model: config, budget, mocked API |
| `test_ollama_provider.py` | 7 | Ollama model: lazy import, config, budget, mocked API |
| `test_context_extractor.py` | 5 | AST function extraction, padding, fallbacks |
| `test_prompt_builder.py` | 4 | Prompt structure, system rules |
| `test_repair_service.py` | 13 | Model routing, safe line-slicing, integration, API endpoints |

All tests run without Docker, external services, or API keys (LLM calls are mocked).

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

- **Lint job**: `ruff check` + `ruff format --check` on `app/` and `tests/`
- **Test job**: Runs after lint passes; `pytest --cov=app` with a minimum 50% coverage gate
- Python 3.11, pip cache enabled for fast runs

### Branching Strategy

```
main ◀── development ◀── feature/QALLM-{id}/{description}
```

- Feature branches off `development`, one branch per Jira story
- PR reviews required before merge
- CI must pass before merge

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and fill in real values:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `data` | Directory for session data storage |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI API key (enables gpt-4o-mini + gpt-5-mini) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Default OpenAI model |
| `ANTHROPIC_API_KEY` | _(empty)_ | Anthropic API key (enables Claude) |
| `ANTHROPIC_MODEL` | `claude-3-5-haiku-20241022` | Default Anthropic model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | Default Ollama model |
| `LLM_DEFAULT_MODEL` | `gpt-4o-mini` | Fallback model when none specified |
| `LLM_STRONG_MODEL` | `gpt-5-mini` | Model for HIGH/CRITICAL (auto routing) |
| `LLM_FAST_MODEL` | `gpt-4o-mini` | Model for MEDIUM/LOW (auto routing) |
| `TOKEN_BUDGET` | `20000` | Max tokens per repair session |
| `MAX_REPAIR_ISSUES` | `10` | Max findings to repair per run |
| `STORAGE_BACKEND` | `local` | Storage backend (local only for PoC) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

Secrets are **never hardcoded**: enforced by CI tests that scan `app/` for credential patterns.

---

## Adding a New Analysis Tool

The registry/strategy architecture makes it straightforward to add new tools:

1. **Analyzer**: Create `app/analyzers/mytool.py`, implement `StaticCodeAnalyzer` (two methods: `tool_name()` and `analyze()`).
2. **Normalizer**: Create `app/normalizers/mytool_normalizer.py`, implement `ToolNormalizer` (set `tool_name` and implement `normalize()`).
3. **Register**: Add both to `app/core/containers.py`.
4. **Test**: Add analyzer + normalizer tests following existing patterns.
5. **Dockerfile**: Install the tool binary/package in the Dockerfile.

The new tool will automatically appear in `/api/analyzers` and run during analysis.

---

## Adding a New LLM Model

The LLM model registry follows the same pattern as the analyzer registry:

1. **Create** `app/llm/my_provider.py` implementing the `LLMModel` interface:
   ```python
   from app.llm.base import LLMModel, LLMResponse, TokenTracker

   class MyModel(LLMModel):
       def name(self) -> str:           # Shown in dropdown
       def is_configured(self) -> bool: # Check API key
       def chat(self, system, user, tracker=None) -> LLMResponse: ...
   ```
2. **Add env vars** to `app/core/config.py` and `.env.example`.
3. **Register** in `app/core/containers.py`:
   ```python
   registry.register(MyModel(model_id="my-model-v1"))
   ```
4. **Test**: Add tests with mocked API calls (see `test_ollama_provider.py` for template).

The new model will immediately appear in the UI dropdown and be selectable via the API.

---

## Sprint Roadmap

### ✅ Sprint 1: Foundation (Weeks 2–3)

| ID | Story | Status |
|----|-------|--------|
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

### 🔧 Sprint 2: LLM Repair (Weeks 3–5)

| ID | Story | Status |
|----|-------|--------|
| QALLM-12 | LLM repair endpoint (targeted code fixes) | ✅ Done |
| QALLM-12c | Multi-model registry + production hardening | ✅ Done |
| QALLM-13 | Token/cost tracking | 🔜 Planned |
| QALLM-14 | Verification (re-run tools after repair) | 🔜 Planned |
| QALLM-20 | OpenAPI documentation | ✅ Done |
| QALLM-21 | Structured JSON logging | ✅ Done |
| QALLM-22 | Enhanced health check | ✅ Done |

### 🔜 Sprint 3: Deployment & Monitoring (Weeks 5–6)

| ID | Story |
|----|-------|
| QALLM-23 | CD pipeline (deploy on merge) |
| QALLM-24 | AWS EC2/ECS deployment |
| QALLM-25 | Integration test suite |
| QALLM-26 | Prometheus + Grafana metrics |

### 🔜 Sprint 4: Observability (Week 7)

| ID | Story |
|----|-------|
| QALLM-27 | CloudWatch dashboard |

---

## Team

| Name | Role | GitHub |
|------|------|--------|
| Gerard García | Product Owner + DevOps | |
| Mohssin Assaban | Scrum Master + DevOps | [@assaban](https://github.com/assaban) |
| Hidde Makimei | Backend + Testing | |
| Oriol Fernandez | Backend + QA + Monitoring | |

**Customer:** Dr. Nafis Islam (UvA)

---

## License

University of Amsterdam (MSc. Software Engineering 2526 DevOps coursework). Not licensed for redistribution.

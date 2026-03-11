# Walkthrough - Microservices Separation (v0.2.0)

## New Service Architecture

- **Front-end**: Nginx-based service that serves the latest UI and acts as a reverse proxy.
- **Session Service**: FastAPI service (v0.2.0) managing sessions, file uploads, and repository cloning.
- **Analysis Service**: FastAPI service (v0.2.0) performing static analysis.
- **LLM Service**: **[NEW]** FastAPI service (v0.2.0) dedicated to LLM-based code repairs and analysis verification.

## Key Changes

### 1. Directory Structure

```
services/
├── frontend/
│   ├── nginx/default.conf
│   └── app/               (Latest UI assets)
├── session/               (v0.2.0)
│   ├── app/
│   │   ├── api/session_routes.py
│   │   └── services/session_service.py
│   └── Dockerfile
├── analysis/              (v0.2.0)
│   ├── app/
│   │   ├── api/analysis_routes.py
│   │   ├── analyzers/
│   │   └── services/analysis_service.py
│   └── Dockerfile
└── llm/                   (v0.2.0 - [NEW])
    ├── app/
    │   ├── api/repair_routes.py
    │   ├── repair/
    │   ├── llm/
    │   └── services/repair_service.py
    └── Dockerfile
```

### 2. Reverse Proxy (Nginx)

The frontend [default.conf](file:///c:/Users/gerar/Desktop/UVA/DEVOPS/Group%20project/UvA-DevOps-Software-QA-LLM-MVP/nginx/default.conf) now routes traffic to four backend endpoints:

- `/api/session/` -> `session-service`
- `/api/analyse`, `/api/analyzers` -> `analysis-service`
- `/api/repair/`, `/api/verify/`, `/api/llm/` -> `llm-service`

### 3. Shared Storage

All three backend services share a Docker volume mounted at `/app/data`. This ensures that `llm-service` can repair files uploaded via `session-service` and `analysis-service` can verify them.

## Legacy Code Removal

The monolithic `app/` and `tests/` directories have been removed. The project structure is now fully service-oriented.

## CI/CD Updates

The GitHub Actions workflow ([.github/workflows/ci.yml](file:///c:/Users/gerar/Desktop/UVA/DEVOPS/Group%20project/UvA-DevOps-Software-QA-LLM-MVP/.github/workflows/ci.yml)) has been updated to:

- Lint the new [services/](file:///c:/Users/gerar/Desktop/UVA/DEVOPS/Group%20project/UvA-DevOps-Software-QA-LLM-MVP/docker-compose.yml-services) directory.
- Run tests independently for both `Session Service` and `Analysis Service`.
- Ensure `PYTHONPATH` is set correctly for service-level testing.

## How to Run

1. Make sure you have Docker and Docker Compose installed.
2. Run the following command in the root directory:
   ```bash
   docker-compose up --build
   ```
3. Access the UI at `http://localhost`.

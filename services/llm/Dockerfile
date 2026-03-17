FROM python:3.11-slim

WORKDIR /app

# Install OS deps: git + patch + curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    git patch curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Static analysis tools (needed for /verify endpoint)
RUN pip install --no-cache-dir bandit ruff radon

# TruffleHog (Go binary) - also needed for /verify
RUN TG_VER="3.88.0" \
    && curl -sSL -o /tmp/trufflehog.tar.gz \
    "https://github.com/trufflesecurity/trufflehog/releases/download/v${TG_VER}/trufflehog_${TG_VER}_linux_amd64.tar.gz" \
    && tar -xzf /tmp/trufflehog.tar.gz -C /tmp trufflehog \
    && mv /tmp/trufflehog /usr/local/bin/trufflehog \
    && chmod +x /usr/local/bin/trufflehog \
    && rm /tmp/trufflehog.tar.gz

# Application code
COPY app ./app

# Persistent data volume mount point
RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8000"]

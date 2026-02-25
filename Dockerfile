FROM python:3.11-slim

WORKDIR /app

# Install OS deps: git + patch + (optional) curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    git patch \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install analysis tools inside image (PoC-friendly)
RUN pip install --no-cache-dir bandit ruff radon \
 && true

# TruffleHog is typically a Go binary. For PoC, install via pip might not exist.
# You can bake it in later or install it in CI.
# RUN ...
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN TG_VER="3.88.0" \
 && curl -sSL -o /tmp/trufflehog.tar.gz \
    "https://github.com/trufflesecurity/trufflehog/releases/download/v${TG_VER}/trufflehog_${TG_VER}_linux_amd64.tar.gz" \
 && tar -xzf /tmp/trufflehog.tar.gz -C /tmp trufflehog \
 && mv /tmp/trufflehog /usr/local/bin/trufflehog \
 && chmod +x /usr/local/bin/trufflehog \
 && trufflehog --version


COPY app ./app
COPY scripts ./scripts

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8000"]

import os

from pydantic import BaseModel


class Settings(BaseModel):
    DATA_DIR: str = os.getenv("DATA_DIR", "data")

    # LLM: OpenAI
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5o-mini")

    # LLM: Anthropic
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

    # LLM: Ollama
    OLLAMA_BASE_URL: str  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str  = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    # LLM — shared
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    TOKEN_BUDGET: int = int(os.getenv("TOKEN_BUDGET", "20000"))
    MAX_REPAIR_ISSUES: int = int(os.getenv("MAX_REPAIR_ISSUES", "10"))

    # Storage (local only for PoC)
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")


settings = Settings()

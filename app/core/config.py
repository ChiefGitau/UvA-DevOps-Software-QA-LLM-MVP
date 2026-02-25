from pydantic import BaseModel
import os

class Settings(BaseModel):
    DATA_DIR: str = os.getenv("DATA_DIR", "data")

    # LLM
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # choose your model
    TOKEN_BUDGET: int = int(os.getenv("TOKEN_BUDGET", "20000"))
    MAX_REPAIR_ISSUES: int = int(os.getenv("MAX_REPAIR_ISSUES", "10"))

    # Storage (local only for PoC)
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")

settings = Settings()

"""Tests for secrets management (QALLM-19)."""
import re
from pathlib import Path


# Patterns that indicate hardcoded secrets (not in demo/ which is intentionally buggy)
SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub Personal Access Token"),
    (r"sk-[A-Za-z0-9]{32,}", "OpenAI API Key"),
    (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password"),
    (r"secret\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret"),
]

APP_DIRS = [Path("app")]


def _scan_files():
    """Yield (file, line_no, pattern_name, line) for any matched secret patterns."""
    for d in APP_DIRS:
        if not d.exists():
            continue
        for py in d.rglob("*.py"):
            text = py.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(text.splitlines(), 1):
                # Skip comments and string type annotations
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for pattern, name in SECRET_PATTERNS:
                    if re.search(pattern, line):
                        yield str(py), i, name, line.strip()


def test_no_hardcoded_secrets_in_app():
    """App code must never contain hardcoded secrets."""
    hits = list(_scan_files())
    if hits:
        msg = "Hardcoded secrets detected:\n"
        for f, line, name, text in hits:
            msg += f"  {f}:{line} [{name}] {text}\n"
        raise AssertionError(msg)


def test_env_example_exists_and_has_content():
    p = Path(".env.example")
    assert p.exists(), ".env.example must exist"
    text = p.read_text()
    assert len(text.strip()) > 0, ".env.example must not be empty"
    assert "OPENAI_API_KEY" in text, ".env.example must document OPENAI_API_KEY"


def test_env_example_has_no_real_values():
    """OPENAI_API_KEY in .env.example must be blank (no real key committed)."""
    text = Path(".env.example").read_text()
    for line in text.splitlines():
        if line.startswith("OPENAI_API_KEY"):
            val = line.split("=", 1)[1].strip()
            assert val == "", f"OPENAI_API_KEY must be blank in .env.example, got: {val}"


def test_gitignore_excludes_env():
    p = Path(".gitignore")
    assert p.exists()
    text = p.read_text()
    assert ".env" in text, ".gitignore must exclude .env"


def test_dockerignore_excludes_env():
    p = Path(".dockerignore")
    assert p.exists()
    text = p.read_text()
    assert ".env" in text, ".dockerignore must exclude .env from image"


def test_config_reads_from_env():
    """Settings must read secrets from environment, not hardcode them."""
    config_text = Path("app/core/config.py").read_text()
    assert "os.getenv" in config_text, "config.py must use os.getenv for secrets"

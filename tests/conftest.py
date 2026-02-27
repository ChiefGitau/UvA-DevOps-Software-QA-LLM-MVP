import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def _use_tmp_data(tmp_path, monkeypatch):
    """Redirect all session data to a temp directory so tests never touch real data."""
    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path / "data"))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_zip() -> bytes:
    """Create an in-memory zip containing a small Python project."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("sample/hello.py", 'import os\npassword = "secret123"\nprint(password)\n')
        zf.writestr("sample/util.py", "def add(a, b):\n    return a + b\n")
    return buf.getvalue()

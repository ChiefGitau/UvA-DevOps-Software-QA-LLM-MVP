from __future__ import annotations
from pathlib import Path

IGNORED_PARTS = {"__MACOSX", ".git", ".venv", "venv", "node_modules", "dist", "build"}

def is_ignored_path(p: str) -> bool:
    if not p:
        return True
    # AppleDouble
    name = Path(p).name
    if name.startswith("._") or name == ".DS_Store":
        return True
    parts = set(Path(p).parts)
    if parts & IGNORED_PARTS:
        return True
    return False

def to_workspace_relative(path_str: str, workspace_dir: Path) -> str:
    """
    Convert absolute paths to workspace-relative when possible.
    Works in Docker (/app/.../workspace/...) and local paths too.
    """
    if not path_str:
        return ""
    s = path_str.replace("\\", "/")
    marker = "/workspace/"
    if marker in s:
        return s.split(marker, 1)[1]
    # attempt realpath relative
    try:
        p = Path(path_str).resolve()
        ws = workspace_dir.resolve()
        if str(p).startswith(str(ws)):
            return str(p.relative_to(ws)).replace("\\", "/")
    except Exception:
        pass
    return path_str.replace("\\", "/")

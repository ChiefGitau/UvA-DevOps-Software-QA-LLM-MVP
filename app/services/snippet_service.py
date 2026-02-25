from pathlib import Path

class SnippetService:
    @staticmethod
    def get_snippet(workspace: Path, file_path: str, line: int | None, context: int = 2) -> str | None:
        if not file_path or not line:
            return None

        rel = file_path.lstrip("./")
        target = (workspace / rel).resolve()

        if not target.exists() or not target.is_file():
            return None

        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            return None

        idx = line - 1
        start = max(0, idx - context)
        end = min(len(lines), idx + context + 1)

        snippet = []
        for i in range(start, end):
            prefix = ">>" if i == idx else "  "
            snippet.append(f"{prefix} {i+1:4d}: {lines[i]}")

        return "\n".join(snippet) if snippet else None

import json
from app.services.session_service import SessionService

class AnalysisService:
    def __init__(self, registry):
        self.registry = registry

    def run(self, session_id: str, selected_tools: list[str] | None = None):
        workspace = SessionService.workspace_dir(session_id)
        reports = SessionService.reports_dir(session_id)
        reports.mkdir(parents=True, exist_ok=True)

        selected = set(selected_tools or [])

        if not workspace.exists() or not any(workspace.rglob("*.py")):
            raise RuntimeError("Active workspace has no Python files. Did you click Apply Selection / Select files?")

        results = []

        for analyzer in self.registry.all():
            if selected and analyzer.tool_name() not in selected:
                continue

            result = analyzer.analyze(workspace, reports)
            results.append(result.__dict__)

        (reports / "analysis_raw_index.json").write_text(
            json.dumps(results, indent=2),
            encoding="utf-8"
        )

        return {"raw_results": results}

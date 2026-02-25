import json
from app.domain.models import Finding, Patch
from app.services.session_service import SessionService
from app.repair.registry import RepairRegistry
from app.repair.base import RepairContext

class RepairService:
    def __init__(self, registry: RepairRegistry):
        self.registry = registry

    def run(self, session_id: str, selected_tools: list[str] | None, model: str, token_budget: int, max_issues: int) -> dict:
        reports = SessionService.reports_dir(session_id)
        ws = SessionService.workspace_dir(session_id)
        patches_dir = SessionService.patches_dir(session_id)
        patches_dir.mkdir(parents=True, exist_ok=True)

        unified_path = reports / "findings_unified.json"
        if not unified_path.exists():
            raise RuntimeError("No unified findings. Run analyse first.")

        items = json.loads(unified_path.read_text(encoding="utf-8") or "[]")
        findings = [self._finding_from_dict(it) for it in items]

        selected = set([t.lower() for t in (selected_tools or [])])
        if selected:
            findings = [f for f in findings if f.tool.lower() in selected]

        sev_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        findings.sort(key=lambda f: sev_rank.get(f.severity, 0), reverse=True)

        ctx = RepairContext(
            session_id=session_id,
            workspace_dir=ws,
            reports_dir=reports,
            patches_dir=patches_dir,
            token_budget=token_budget,
            model=model
        )

        patches: list[Patch] = []
        remaining_budget = token_budget

        for f in findings:
            if len(patches) >= max_issues:
                break

            repairer = self.registry.pick(f)
            if not repairer:
                patches.append(Patch(finding_id=f.id, description="No repairer registered.", unified_diff="", applied=False, error="NO_REPAIRER"))
                continue

            # Let each repairer optionally consume tokens; LLM returns in meta
            p = repairer.repair(f, ctx)
            patches.append(p)

            used = 0
            try:
                used = int((p.meta or {}).get("tokens_used", 0))
            except Exception:
                used = 0
            remaining_budget -= used
            ctx.token_budget = remaining_budget
            if remaining_budget <= 0:
                break

        (patches_dir / "patches.json").write_text(json.dumps([p.__dict__ for p in patches], indent=2), encoding="utf-8")
        (reports / "token_usage.json").write_text(json.dumps({"model": model, "budget": token_budget, "used": token_budget - remaining_budget}, indent=2), encoding="utf-8")

        return {
            "patches": [p.__dict__ for p in patches],
            "token_usage": {"model": model, "budget": token_budget, "used": token_budget - remaining_budget}
        }

    def _finding_from_dict(self, d: dict) -> Finding:
        return Finding(
            tool=d.get("tool",""),
            type=d.get("type","OTHER"),
            severity=d.get("severity","LOW"),
            file=d.get("file",""),
            line=d.get("line"),
            message=d.get("message",""),
            rule_id=d.get("rule_id"),
            code_snippet=d.get("code_snippet"),
            extra=d.get("extra") or {}
        )

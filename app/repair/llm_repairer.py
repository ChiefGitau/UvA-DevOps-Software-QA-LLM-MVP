import json
from pathlib import Path
from app.domain.models import Finding, Patch
from .base import FindingRepairer, RepairContext
from app.services.patch_service import PatchService
from app.llm.openai_client import OpenAiLlmClient

class LlmFindingRepairer(FindingRepairer):
    def __init__(self, llm_client: OpenAiLlmClient):
        self.llm = llm_client

    def supports(self, finding: Finding) -> bool:
        # You can tune this: fix SECURITY/SECRET/SMELL only
        return finding.type in ("SECURITY", "SECRET", "SMELL")

    def repair(self, finding: Finding, ctx: RepairContext) -> Patch:
        if not self.llm.enabled():
            return Patch(
                finding_id=finding.id,
                description="LLM disabled (missing OPENAI_API_KEY).",
                unified_diff="",
                applied=False,
                error="NO_API_KEY"
            )

        prompt = self._build_prompt(finding, ctx.workspace_dir)
        diff, tokens = self.llm.generate_unified_diff(ctx.model, prompt)

        if not diff.strip():
            return Patch(
                finding_id=finding.id,
                description="LLM returned empty diff.",
                unified_diff="",
                applied=False,
                error="NO_PATCH",
                meta={"tokens_used": tokens, "model": ctx.model}
            )

        try:
            PatchService.apply_unified_diff(ctx.session_id, diff)
            return Patch(
                finding_id=finding.id,
                description=f"LLM auto-fix ({finding.tool}:{finding.rule_id})",
                unified_diff=diff,
                applied=True,
                meta={"tokens_used": tokens, "model": ctx.model}
            )
        except Exception as e:
            return Patch(
                finding_id=finding.id,
                description="LLM patch apply failed.",
                unified_diff=diff,
                applied=False,
                error=str(e),
                meta={"tokens_used": tokens, "model": ctx.model}
            )

    def _build_prompt(self, finding: Finding, workspace_dir: Path) -> str:
        # best-effort context snippet
        snippet = ""
        fp = (workspace_dir / finding.file).resolve()
        if fp.exists() and fp.is_file():
            snippet = self._read_context(fp, finding.line or 1, radius=25)

        return f"""You are a DevSecOps code repair assistant.

Fix exactly ONE issue described below.

FINDING (JSON):
{json.dumps(finding.to_dict(), indent=2)}

CODE CONTEXT:
{snippet}

STRICT OUTPUT RULES:
1) Output ONLY a unified diff (git patch) starting with 'diff --git'.
2) No explanations, no markdown, no extra text.
3) Minimal change; do not modify unrelated code.
"""

    def _read_context(self, file_path: Path, line: int, radius: int = 25) -> str:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        start = max(0, line - radius - 1)
        end = min(len(lines), line + radius)
        chunk = lines[start:end]
        return "\n".join(f"{i+1:>4}: {txt}" for i, txt in enumerate(chunk, start=start))

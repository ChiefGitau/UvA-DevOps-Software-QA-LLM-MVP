"""Repair service: orchestrates LLM-based code repair (QALLM-12 / US-08).

Flow:
  1. Load persisted findings from findings_unified.json
  2. Sort by severity (CRITICAL first) and cap at MAX_REPAIR_ISSUES
  3. For each finding:
     a. Extract surrounding function/class context
     b. Build a targeted prompt
     c. Call the selected LLM provider via the registry
     d. Diff the original vs repaired code → unified diff
     e. Create a Patch object
  4. Persist patches + token usage as repair_report.json
"""

from __future__ import annotations

import difflib
import json
import logging
from dataclasses import asdict
from pathlib import Path

from app.core.config import settings
from app.core.containers import build_llm_registry
from app.domain.models import Finding, Patch
from app.llm.base import LLMResponse, TokenTracker
from app.repair.context_extractor import extract_function_context
from app.repair.prompt_builder import SYSTEM_PROMPT, build_repair_prompt
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

# Module-level registry (built once)
_llm_registry = build_llm_registry()


def _load_findings(session_id: str) -> list[Finding]:
    """Load persisted findings from the session's reports directory."""
    p = SessionService.reports_dir(session_id) / "findings_unified.json"
    if not p.exists():
        return []

    raw = json.loads(p.read_text(encoding="utf-8"))
    findings = []
    for r in raw:
        r.pop("id", None)
        r.pop("extra", None)
        try:
            findings.append(Finding(**r))
        except TypeError:
            continue
    return findings


def _make_diff(
    original: str,
    repaired: str,
    filename: str,
    start_line: int,
) -> str:
    """Generate a unified diff between original and repaired code."""
    orig_lines = original.splitlines(keepends=True)
    fix_lines = repaired.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        fix_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "".join(diff)


def _apply_repair_to_file(
    filepath: Path,
    original_context: str,
    repaired_context: str,
) -> bool:
    """Replace the original context in the file with the repaired version."""
    if not filepath.exists():
        return False

    source = filepath.read_text(encoding="utf-8", errors="replace")
    if original_context not in source:
        return False

    new_source = source.replace(original_context, repaired_context, 1)
    if new_source == source:
        return False

    filepath.write_text(new_source, encoding="utf-8")
    return True


def list_providers() -> dict:
    """Return available and configured LLM providers."""
    return {
        "available": _llm_registry.list(),
        "configured": _llm_registry.list_configured(),
        "default": settings.LLM_PROVIDER,
    }


def run_repair(
    session_id: str,
    finding_ids: list[str] | None = None,
    max_issues: int | None = None,
    provider: str | None = None,
) -> dict:
    """Run LLM repair on findings for a session.

    Parameters
    ----------
    session_id : str
        Session UUID.
    finding_ids : list[str] | None
        Specific finding IDs to repair. If None, repairs top-N by severity.
    max_issues : int | None
        Override MAX_REPAIR_ISSUES from config.
    provider : str | None
        LLM provider name (e.g. "openai", "anthropic").
        Falls back to LLM_PROVIDER env var, then first configured provider.

    Returns
    -------
    dict
        {patches, token_usage, repaired_count, provider_used}
    """
    cap = max_issues or settings.MAX_REPAIR_ISSUES
    workspace = SessionService.workspace_active_dir(session_id)
    reports = SessionService.reports_dir(session_id)

    # Resolve provider
    provider_name = provider or settings.LLM_PROVIDER
    llm = _llm_registry.pick(provider_name)

    # 1. Load findings
    findings = _load_findings(session_id)
    if not findings:
        return {"patches": [], "token_usage": {}, "repaired_count": 0, "provider_used": provider_name}

    # 2. Filter / sort
    if finding_ids:
        id_set = set(finding_ids)
        findings = [f for f in findings if f.id in id_set]
    else:
        findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 99))

    findings = findings[:cap]
    findings = [f for f in findings if f.type != "SECRET"]

    # 3. Repair loop
    tracker = TokenTracker(budget=settings.TOKEN_BUDGET)
    patches: list[Patch] = []

    for finding in findings:
        if tracker.remaining <= 0:
            logger.warning(
                "Token budget exhausted after %d calls",
                tracker.calls,
                extra={"session_id": session_id},
            )
            break

        filepath = workspace / finding.file
        context, start_line = extract_function_context(filepath, finding.line)

        if not context.strip():
            patches.append(
                Patch(
                    finding_id=finding.id,
                    description=f"Could not extract context for {finding.file}:{finding.line}",
                    unified_diff="",
                    error="no_context",
                )
            )
            continue

        user_prompt = build_repair_prompt(finding, context, start_line)
        logger.info(
            "Repairing %s:%s [%s] via %s",
            finding.file,
            finding.line,
            finding.rule_id or finding.tool,
            provider_name,
            extra={"session_id": session_id},
        )

        resp: LLMResponse = llm.chat(SYSTEM_PROMPT, user_prompt, tracker)

        if resp.error:
            patches.append(
                Patch(
                    finding_id=finding.id,
                    description=f"LLM error: {resp.error}",
                    unified_diff="",
                    error=resp.error,
                    meta={"model": resp.model, "provider": resp.provider},
                )
            )
            continue

        repaired = resp.content.strip()
        if repaired.startswith("```"):
            lines = repaired.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            repaired = "\n".join(lines)

        diff = _make_diff(context, repaired, finding.file, start_line)

        if not diff.strip():
            patches.append(
                Patch(
                    finding_id=finding.id,
                    description="No change needed (possible false positive)",
                    unified_diff="",
                    meta={"model": resp.model, "provider": resp.provider},
                )
            )
            continue

        applied = _apply_repair_to_file(filepath, context, repaired)
        patches.append(
            Patch(
                finding_id=finding.id,
                description=f"Fixed {finding.tool} {finding.rule_id or ''}: {finding.message[:80]}",
                unified_diff=diff,
                applied=applied,
                meta={"model": resp.model, "provider": resp.provider},
            )
        )

    # 4. Persist
    report = {
        "session_id": session_id,
        "provider": provider_name,
        "patches": [asdict(p) for p in patches],
        "token_usage": tracker.to_dict(),
    }
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "repair_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    repaired_count = sum(1 for p in patches if p.applied)
    logger.info(
        "Repair complete via %s: %d/%d patches applied, %d tokens used",
        provider_name,
        repaired_count,
        len(patches),
        tracker.total_tokens,
        extra={"session_id": session_id},
    )

    return {
        "patches": [asdict(p) for p in patches],
        "token_usage": tracker.to_dict(),
        "repaired_count": repaired_count,
        "provider_used": provider_name,
    }

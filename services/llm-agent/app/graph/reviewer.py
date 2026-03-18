from __future__ import annotations

import json
import logging

from app.core.config import settings
from app.core.containers import build_llm_registry
from app.graph.state import AgentState, PatchResult

logger = logging.getLogger(__name__)

REVIEWER_SYSTEM_PROMPT = """\
You are a senior Python code reviewer. You will receive a unified diff produced
by another agent. Verify:
1. The diff compiles (no syntax errors).
2. The diff addresses ONLY the reported finding — no unrelated changes.
3. The fix is correct and does not introduce new issues.

Respond with JSON only:
{"approved": true}
or
{"approved": false, "reason": "<short explanation>"}\
"""


def _build_review_prompt(patch: PatchResult) -> str:
    return (
        f"Tool: {patch['tool']}\n"
        f"Finding: {patch['description']}\n"
        f"File: {patch['file']}\n\n"
        f"Diff:\n{patch['unified_diff']}"
    )


def reviewer_node(state: AgentState) -> dict:
    """
    Reviews every patch with a non-empty diff.
    Attaches reviewer_note to each patch; marks applied=False for rejections.
    """
    patches: list[PatchResult] = list(state.get("patches", []))
    if not patches:
        return {"patches": [], "review_notes": []}

    registry = build_llm_registry()
    try:
        reviewer_model = registry.pick(settings.LLM_REVIEWER_MODEL)
    except ValueError:
        m = registry.get_default()
        if m is None:
            logger.warning("reviewer: no LLM configured, skipping review")
            return {"patches": [], "review_notes": []}
        reviewer_model = m

    reviewed_patches: list[PatchResult] = []
    review_notes: list[dict] = []

    for patch in patches:
        # Skip patches that already failed or have no diff to review
        if not patch.get("unified_diff") or not patch.get("applied"):
            reviewed_patches.append(patch)
            continue

        prompt = _build_review_prompt(patch)
        resp = reviewer_model.chat(system=REVIEWER_SYSTEM_PROMPT, user=prompt)

        if resp.error:
            logger.warning(
                "reviewer: LLM error for finding %s: %s",
                patch["finding_id"],
                resp.error,
            )
            reviewed_patches.append(patch)
            continue

        try:
            review = json.loads(resp.content.strip())
        except (json.JSONDecodeError, ValueError):
            # Non-parseable response — treat as approved to avoid blocking
            logger.warning(
                "reviewer: unparseable response for %s, treating as approved",
                patch["finding_id"],
            )
            reviewed_patches.append(patch)
            continue

        approved = review.get("approved", True)
        reason = review.get("reason")

        updated: PatchResult = dict(patch)  # type: ignore[assignment]
        updated["reviewer_note"] = reason if not approved else None
        if not approved:
            updated["applied"] = False
            logger.info(
                "reviewer: REJECTED finding %s — %s", patch["finding_id"], reason
            )
        else:
            logger.info("reviewer: approved finding %s", patch["finding_id"])

        reviewed_patches.append(updated)  # type: ignore[arg-type]
        review_notes.append({
            "finding_id": patch["finding_id"],
            "approved": approved,
            "reason": reason,
        })

    # Return as delta — the reducer appends these to existing state lists
    return {"patches": reviewed_patches, "review_notes": review_notes}

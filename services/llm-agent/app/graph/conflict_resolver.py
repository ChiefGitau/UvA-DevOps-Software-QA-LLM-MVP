from __future__ import annotations

import logging

from app.graph.agents.bandit import BanditAgent
from app.graph.agents.radon import RadonAgent
from app.graph.agents.ruff import RuffAgent
from app.graph.agents.trufflehog import TruffleHogAgent
from app.graph.state import AgentState

logger = logging.getLogger(__name__)

_AGENT_MAP = {
    "bandit": BanditAgent,
    "ruff": RuffAgent,
    "radon_cc": RadonAgent,
    "trufflehog": TruffleHogAgent,
}


def conflict_resolver_node(state: AgentState) -> dict:
    """
    Runs deferred (contested-file) tasks sequentially in priority order.
    Each task reads the current workspace file — which may already have been
    patched by a higher-priority agent — so the changes compose cleanly.
    """
    queued = state.get("queued_tasks", [])
    if not queued:
        return {"patches": [], "errors": []}

    provider = state.get("provider")
    all_patches = []
    all_errors = []

    for task in queued:
        tool = task["tool"]
        agent_cls = _AGENT_MAP.get(tool)
        if agent_cls is None:
            logger.warning("conflict_resolver: unknown tool '%s', skipping", tool)
            continue

        logger.info(
            "conflict_resolver: running %s on %d deferred finding(s) for files: %s",
            tool,
            len(task["findings"]),
            task["files"],
        )
        try:
            agent = agent_cls(session_id=state["session_id"], provider=provider)
            result = agent.run(task)
            all_patches.extend(result.get("patches", []))
            all_errors.extend(result.get("errors", []))
        except Exception as e:
            logger.error("conflict_resolver: %s agent failed: %s", tool, e)
            for f in task["findings"]:
                all_errors.append(
                    {
                        "finding_id": f.get("id", ""),
                        "file": f.get("file", ""),
                        "tool": tool,
                        "error": str(e),
                    }
                )

    return {"patches": all_patches, "errors": all_errors}

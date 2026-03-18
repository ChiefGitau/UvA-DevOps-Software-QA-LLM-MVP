from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graph.agents.bandit import bandit_node
from app.graph.agents.radon import radon_node
from app.graph.agents.ruff import ruff_node
from app.graph.agents.trufflehog import trufflehog_node
from app.graph.conflict_resolver import conflict_resolver_node
from app.graph.dispatcher import dispatcher_node
from app.graph.orchestrator import orchestrator_node
from app.graph.reviewer import reviewer_node
from app.graph.state import AgentState

# ---------------------------------------------------------------------------
# Routing function — unconditional fan-out to all four tool nodes after
# dispatcher. Each node checks whether it has work in parallel_tasks and
# returns empty results if not, so unused nodes are harmless no-ops.
# ---------------------------------------------------------------------------


def _route_to_tools(state: AgentState) -> list[str]:
    active_tools = {t["tool"] for t in state.get("parallel_tasks", [])}
    node_map = {
        "bandit": "bandit_node",
        "ruff": "ruff_node",
        "radon_cc": "radon_node",
        "trufflehog": "trufflehog_node",
    }
    targets = [node_map[tool] for tool in active_tools if tool in node_map]
    # Always return at least one destination so the graph doesn't stall
    return targets or ["conflict_resolver"]


# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

builder: StateGraph = StateGraph(AgentState)

builder.add_node("dispatcher", dispatcher_node)
builder.add_node("bandit_node", bandit_node)
builder.add_node("ruff_node", ruff_node)
builder.add_node("radon_node", radon_node)
builder.add_node("trufflehog_node", trufflehog_node)
builder.add_node("conflict_resolver", conflict_resolver_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("orchestrator", orchestrator_node)

builder.set_entry_point("dispatcher")

# Fan-out: dispatcher → (only the tool nodes that have work)
builder.add_conditional_edges(
    "dispatcher",
    _route_to_tools,
    {
        "bandit_node": "bandit_node",
        "ruff_node": "ruff_node",
        "radon_node": "radon_node",
        "trufflehog_node": "trufflehog_node",
        "conflict_resolver": "conflict_resolver",
    },
)

# Fan-in: all tool nodes → conflict resolver
for _tool_node in ["bandit_node", "ruff_node", "radon_node", "trufflehog_node"]:
    builder.add_edge(_tool_node, "conflict_resolver")

builder.add_edge("conflict_resolver", "reviewer")
builder.add_edge("reviewer", "orchestrator")
builder.add_edge("orchestrator", END)

graph = builder.compile()

"""LangGraph pipeline with guardrail nodes and a safe-refusal path.

InputGuard -> MarketAnalyst -> LogisticsCoordinator -> InventoryStrategist
           -> ExecutiveOrchestrator -> OutputGuard -> END
Any guard failure routes to SafeRefusal -> END.
"""
from __future__ import annotations

import uuid
from typing import Optional

from langgraph.graph import END, StateGraph

from . import config
from .agents import LLM, SupplyChainAgents
from .guardrails import audit
from .guardrails.input_guard import guard_user_input
from .guardrails.output_guard import guard_agent_output, validate_final_report
from .guardrails.sanitizer import new_nonce
from .state import AgentState
from .tools import ToolRegistry

OUTPUT_FIELDS = {
    "MarketAnalyst": "market_risk_report",
    "LogisticsCoordinator": "logistics_impact",
    "InventoryStrategist": "inventory_risk_level",
}


def _event(state, stage, decision, rules=None, content="", detail=""):
    ev = audit.make_event(state.get("run_id", "-"), stage, decision, rules, content, detail)
    audit.write_event(ev)
    return ev


def input_guard_node(state: AgentState):
    run_id, nonce, canary = uuid.uuid4().hex[:12], new_nonce(), "CANARY-" + new_nonce()
    base = {"run_id": run_id, "nonce": nonce, "canary": canary}
    res = guard_user_input(state.get("query"))
    raw = state.get("query") if isinstance(state.get("query"), str) else ""
    ev = _event(base, "input_guard", "allow" if res.ok else "block", res.rules, raw, res.reason)
    if not res.ok:
        return {**base, "blocked": True, "block_reason": res.reason, "security_events": [ev],
                "history": ["Input blocked by guardrails"]}
    return {**base, "blocked": False, "sanitized_query": res.clean, "security_events": [ev],
            "history": ["Input validated"]}


def make_guarded(name: str, fn):
    """Wrap an agent node: run it, then inspect/clean what it produced."""
    def node(state: AgentState):
        try:
            update = fn(state)
        except Exception as exc:                     # tool not allow-listed, LLM error, ...
            rules = getattr(exc, "rules", ["agent_error"])
            ev = _event(state, name, "block", rules, detail=type(exc).__name__)
            return {"blocked": True, "block_reason": f"{name} failed a safety check.",
                    "security_events": [ev], "history": [f"{name} halted"]}
        field = OUTPUT_FIELDS.get(name)
        if field:
            res = guard_agent_output(update[field], canary=state["canary"], nonce=state["nonce"])
            ev = _event(state, name, "block" if res.blocked else "allow", res.rules + res.redactions, update[field])
            if res.blocked:
                return {"blocked": True, "block_reason": f"{name} output rejected: {res.reason}",
                        "security_events": [ev], "history": [f"{name} output quarantined"]}
            update[field] = res.text
            update["security_events"] = [ev]
        return update
    node.__name__ = name
    return node


def output_guard_node(state: AgentState):
    res = validate_final_report(state["final_recommendation"])
    ev = _event(state, "output_guard", "block" if res.blocked else "allow", res.rules + res.redactions,
                state["final_recommendation"], res.reason)
    if res.blocked:
        return {"blocked": True, "block_reason": res.reason, "final_recommendation": "",
                "actions": [], "requires_human_approval": False, "security_events": [ev],
                "history": ["Final report blocked"]}
    return {"final_recommendation": res.text, "security_events": [ev], "history": ["Final report released"]}


def safe_refusal_node(state: AgentState):
    msg = ("REQUEST BLOCKED BY SECURITY GUARDRAILS\n"
           f"Reason: {state.get('block_reason', 'Unspecified')}\n"
           "No analysis was produced. Please submit a plain region name, e.g. 'South China Sea'.")
    return {"final_recommendation": msg, "actions": [], "requires_human_approval": False,
            "history": ["Safe refusal returned"]}


def _route(state: AgentState) -> str:
    return "blocked" if state.get("blocked") else "continue"


def create_supply_chain_graph(llm: Optional[LLM] = None, tools: Optional[ToolRegistry] = None):
    agents = SupplyChainAgents(llm=llm, tools=tools)
    wf = StateGraph(AgentState)

    wf.add_node("InputGuard", input_guard_node)
    wf.add_node("MarketAnalyst", make_guarded("MarketAnalyst", agents.market_analyst))
    wf.add_node("LogisticsCoordinator", make_guarded("LogisticsCoordinator", agents.logistics_coordinator))
    wf.add_node("InventoryStrategist", make_guarded("InventoryStrategist", agents.inventory_strategist))
    wf.add_node("ExecutiveOrchestrator", make_guarded("ExecutiveOrchestrator", agents.executive_orchestrator))
    wf.add_node("OutputGuard", output_guard_node)
    wf.add_node("SafeRefusal", safe_refusal_node)

    wf.set_entry_point("InputGuard")
    chain = ["InputGuard", "MarketAnalyst", "LogisticsCoordinator", "InventoryStrategist",
             "ExecutiveOrchestrator", "OutputGuard"]
    for cur, nxt in zip(chain, chain[1:]):
        wf.add_conditional_edges(cur, _route, {"continue": nxt, "blocked": "SafeRefusal"})
    wf.add_conditional_edges("OutputGuard", _route, {"continue": END, "blocked": "SafeRefusal"})
    wf.add_edge("SafeRefusal", END)
    return wf.compile()


def run(region: str, llm: Optional[LLM] = None, tools: Optional[ToolRegistry] = None) -> AgentState:
    graph = create_supply_chain_graph(llm, tools)
    return graph.invoke({"query": region, "history": [], "security_events": []},
                        config={"recursion_limit": config.GRAPH_RECURSION_LIMIT})

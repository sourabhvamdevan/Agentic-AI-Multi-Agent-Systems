"""The four agents. Each returns a partial state update; the graph wraps
them with guardrails (see graph.py).

Without an LLM the agents run as deterministic simulations (as in the
original PoC). Pass `llm=callable(system, user) -> str` to use a real model:
the prompts are already built with spotlighting + canary protection.
"""
from __future__ import annotations

from typing import Callable, Optional

from . import config
from .guardrails.policy import evaluate_actions
from .guardrails.sanitizer import build_system_prompt, wrap_untrusted
from .tools import ToolRegistry

LLM = Callable[[str, str], str]

# Illustrative simulation constants (replace with ERP / real data).
LEAD_TIME_INCREASE_DAYS = 14
SAFETY_STOCK_DAYS = 10
DAILY_DEMAND_UNITS = 125
CRITICAL_SKU = "CH-900"


def _strip_label(text: str) -> str:
    return text.split(": ", 1)[1] if text.startswith(("MARKET ANALYST", "LOGISTICS COORDINATOR", "INVENTORY STRATEGIST")) else text


class SupplyChainAgents:
    def __init__(self, llm: Optional[LLM] = None, tools: Optional[ToolRegistry] = None):
        self.llm = llm
        self.tools = tools or ToolRegistry()

    # -- helper: build + run a hardened LLM call ------------------------------
    def _ask_llm(self, state, role: str, task: str, data: dict[str, str]) -> str:
        system = build_system_prompt(role, task, state["nonce"], state["canary"])
        user = "\n\n".join(wrap_untrusted(v, k, state["nonce"]) for k, v in data.items())
        return self.llm(system, user)  # type: ignore[misc]

    # -- Agent 1: Market Analyst ----------------------------------------------
    def market_analyst(self, state):
        region = state["sanitized_query"]
        signal = self.tools.call("news_signals", region=region)      # untrusted tool output
        if self.llm:
            body = self._ask_llm(state, "Global Market Analyst",
                                 "Summarise geopolitical/economic risk signals in 2 sentences.",
                                 {"region": region, "news_feed": signal})
        else:
            body = signal
        return {"market_risk_report": f"MARKET ANALYST: {body}",
                "history": ["Market Analysis Completed"]}

    # -- Agent 2: Logistics Coordinator ---------------------------------------
    def logistics_coordinator(self, state):
        if self.llm:
            body = self._ask_llm(state, "Logistics Coordinator",
                                 "Estimate transit delay impact in 2 sentences.",
                                 {"market_report": state["market_risk_report"]})
        else:
            body = (f"Based on the market signals, rerouting is expected via Cape of Good Hope. "
                    f"Lead times projected to increase by {LEAD_TIME_INCREASE_DAYS} days.")
        return {"logistics_impact": f"LOGISTICS COORDINATOR: {body}",
                "history": ["Logistics Assessment Completed"]}

    # -- Agent 3: Inventory Strategist ----------------------------------------
    def inventory_strategist(self, state):
        gap = max(0, LEAD_TIME_INCREASE_DAYS - SAFETY_STOCK_DAYS)   # numeric, never LLM-derived
        if self.llm:
            body = self._ask_llm(state, "Inventory Strategist",
                                 f"State the stock-out risk. Facts: safety stock {SAFETY_STOCK_DAYS} days, "
                                 f"gap {gap} days, SKU {CRITICAL_SKU}.",
                                 {"logistics_impact": state["logistics_impact"]})
        else:
            body = (f"Current safety stock lasts {SAFETY_STOCK_DAYS} days. The projected delay will cause "
                    f"a stockout gap of {gap} days for critical SKU:{CRITICAL_SKU}.")
        return {"inventory_risk_level": f"INVENTORY STRATEGIST: {body}",
                "stock_gap_days": gap, "history": ["Inventory Risk Assessment Completed"]}

    # -- Agent 4: Executive Orchestrator --------------------------------------
    def executive_orchestrator(self, state):
        gap = state.get("stock_gap_days", 0)
        actions: list[dict] = []
        if gap > 0:
            actions.append({"type": "AIR_FREIGHT", "sku": CRITICAL_SKU, "quantity": gap * DAILY_DEMAND_UNITS})
            actions.append({"type": "ACTIVATE_BACKUP_SUPPLIER", "supplier_region": "Mexico"})
        else:
            actions.append({"type": "MONITOR"})

        decisions = evaluate_actions(actions)                       # policy engine gate
        lines, any_approval = [], False
        for d in decisions:
            if not d.allowed:
                lines.append(f"- REJECTED by policy: {d.action.get('type')} ({d.reason})")
                continue
            a = d.action
            label = a["type"].replace("_", " ").title()
            extra = f" {a['quantity']} units of {a['sku']}" if "quantity" in a else \
                    (f" ({a['supplier_region']})" if "supplier_region" in a else "")
            tag = " [REQUIRES HUMAN APPROVAL]" if d.needs_approval else ""
            any_approval |= d.needs_approval
            lines.append(f"- {label}{extra}{tag}")

        summary = ("Immediate risk of stockout for critical SKUs." if gap > 0
                   else "No stock-out expected; continue monitoring.")
        report = (
            "### STRATEGIC SUPPLY CHAIN RISK REPORT\n"
            f"1. MARKET: {_strip_label(state['market_risk_report'])}\n"
            f"2. LOGISTICS: {_strip_label(state['logistics_impact'])}\n"
            f"3. INVENTORY: {_strip_label(state['inventory_risk_level'])}\n\n"
            f"**EXECUTIVE SUMMARY**: {summary}\n"
            "**RECOMMENDED ACTION** (advisory - nothing is executed automatically):\n" + "\n".join(lines) + "\n"
        )
        return {"final_recommendation": report,
                "actions": [d.action for d in decisions if d.allowed],
                "requires_human_approval": any_approval,
                "history": ["Final Recommendation Generated"]}

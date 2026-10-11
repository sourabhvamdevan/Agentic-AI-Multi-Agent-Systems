import operator
from typing import Annotated, List, TypedDict


class AgentState(TypedDict, total=False):
    # --- input / run metadata
    query: str                    # raw, untrusted user input
    sanitized_query: str          # validated + normalised input
    run_id: str
    nonce: str                    # per-run spotlighting delimiter
    canary: str                   # per-run prompt-leak canary
    # --- control flow
    blocked: bool
    block_reason: str
    # --- agent outputs (all passed through guardrails)
    market_risk_report: str
    logistics_impact: str
    inventory_risk_level: str
    stock_gap_days: int
    final_recommendation: str
    # --- policy-checked recommendations
    actions: List[dict]
    requires_human_approval: bool
    # --- append-only trails
    history: Annotated[List[str], operator.add]
    security_events: Annotated[List[dict], operator.add]

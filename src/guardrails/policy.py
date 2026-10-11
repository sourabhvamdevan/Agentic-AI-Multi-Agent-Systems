"""Layer 5 - action policy engine (least privilege + human-in-the-loop).

LLM text NEVER drives actions. Actions are produced from structured
numbers and then checked here against an allow-list, quantity limits and
approval rules. The system only *recommends*; it has no execute path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .. import config


@dataclass
class ActionDecision:
    action: dict
    allowed: bool
    needs_approval: bool
    reason: str


def evaluate_action(action: dict) -> ActionDecision:
    atype = action.get("type")
    if atype not in config.ALLOWED_ACTIONS:
        return ActionDecision(action, False, False, f"Action type {atype!r} is not on the allow-list.")

    sku = action.get("sku")
    if sku is not None and not (isinstance(sku, str) and re.fullmatch(config.SKU_REGEX, sku)):
        return ActionDecision(action, False, False, "Invalid SKU format.")

    qty = action.get("quantity")
    if qty is not None:
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            return ActionDecision(action, False, False, "Quantity must be a positive integer.")
        if qty > config.HARD_QTY_LIMIT:
            return ActionDecision(action, False, False, f"Quantity exceeds hard limit ({config.HARD_QTY_LIMIT}).")

    needs = atype in config.ALWAYS_NEEDS_APPROVAL or (qty or 0) > config.APPROVAL_QTY_THRESHOLD
    reason = "Human approval required before execution." if needs else "Within autonomous limits (advisory only)."
    return ActionDecision(action, True, needs, reason)


def evaluate_actions(actions: list[dict]) -> list[ActionDecision]:
    return [evaluate_action(a) for a in actions]

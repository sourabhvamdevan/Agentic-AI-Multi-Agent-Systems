"""Central security & runtime configuration.

Every limit lives here so it can be reviewed (and tuned) in one place.
Values can be overridden with environment variables where it makes sense.
"""
from __future__ import annotations

import os

# ---- Input limits -----------------------------------------------------------
MAX_INPUT_CHARS = 80
MIN_INPUT_CHARS = 3
# Letters (any language), digits, space and a few harmless punctuation marks.
# Deliberately excludes : / \ < > ` " { } [ ] | ; = $ % @ # ! ? * ~ ^
ALLOWED_INPUT_REGEX = r"^[\w \-,.'&()]+$"

# ---- Injection scoring ------------------------------------------------------
# Each detection rule carries a weight; a text is blocked when the summed
# weight reaches BLOCK_THRESHOLD. Lower scores are logged and neutralised.
BLOCK_THRESHOLD = 3

# ---- Agent / tool limits ----------------------------------------------------
MAX_AGENT_OUTPUT_CHARS = 1_500
MAX_REPORT_CHARS = 4_000
GRAPH_RECURSION_LIMIT = 12          # hard cap on graph steps (loop protection)
ALLOWED_TOOLS = frozenset({"news_signals"})

# ---- Action policy (least privilege / human-in-the-loop) --------------------
ALLOWED_ACTIONS = frozenset(
    {"AIR_FREIGHT", "ACTIVATE_BACKUP_SUPPLIER", "INCREASE_SAFETY_STOCK", "MONITOR"}
)
ALWAYS_NEEDS_APPROVAL = frozenset({"ACTIVATE_BACKUP_SUPPLIER"})
APPROVAL_QTY_THRESHOLD = 250        # above this a human must sign off
HARD_QTY_LIMIT = 5_000              # above this the action is rejected outright
SKU_REGEX = r"^[A-Z]{2}-\d{3,4}$"

# ---- Audit ------------------------------------------------------------------
AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "logs/audit.jsonl")

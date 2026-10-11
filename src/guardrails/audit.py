"""Tamper-evident-ish structured audit log (JSON Lines).

Stores rule names, hashes and lengths - never the raw (possibly malicious
or sensitive) content - so the log itself can't become a leak or an
injection vector.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from .. import config


def fingerprint(text: str) -> dict:
    return {"sha256": hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16], "len": len(text)}


def make_event(run_id: str, stage: str, decision: str, rules: list[str] | None = None,
               content: str = "", detail: str = "") -> dict:
    ev = {"ts": round(time.time(), 3), "run_id": run_id, "stage": stage,
          "decision": decision, "rules": rules or [], "detail": detail}
    if content:
        ev["content"] = fingerprint(content)
    return ev


def write_event(event: dict) -> None:
    path = Path(os.getenv("AUDIT_LOG_PATH", config.AUDIT_LOG_PATH))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=True) + "\n")
    except OSError:
        pass  # logging must never crash the pipeline

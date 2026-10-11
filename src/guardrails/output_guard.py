"""Layer 3/4 - inspect what agents (and tools) produce.

* Treat every agent/tool output as untrusted: it may carry an *indirect*
  injection from a poisoned data source, or a leaked system prompt.
* Strip anything that can act as an exfiltration channel (URLs, images, HTML).
* Redact secrets and personal data before they reach state, logs or the user.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .. import config
from .injection import Detection, Finding, detect
from .sanitizer import normalize

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("openai_style_key", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(-----END [A-Z ]*PRIVATE KEY-----|$)", re.S)),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{20,}\b")),
    ("email_address", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
]
URL_RE = re.compile(r"\b(?:https?|ftp)://\S+|\bwww\.\S+", re.I)
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
HTML_TAG_RE = re.compile(r"<[^>]{1,200}>")


@dataclass
class OutputResult:
    text: str
    blocked: bool = False
    reason: str = ""
    rules: list[str] = field(default_factory=list)
    redactions: list[str] = field(default_factory=list)


def redact_sensitive(text: str) -> tuple[str, list[str]]:
    hits: list[str] = []
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            hits.append(name)
            text = pattern.sub("[REDACTED]", text)
    return text, hits


def strip_active_content(text: str) -> tuple[str, list[str]]:
    hits: list[str] = []
    for name, pattern, repl in (
        ("markdown_image", MD_IMAGE_RE, "[image removed]"),
        ("url", URL_RE, "[link removed]"),
        ("html_tag", HTML_TAG_RE, ""),
    ):
        if pattern.search(text):
            hits.append(name)
            text = pattern.sub(repl, text)
    return text, hits


def guard_agent_output(text: str, *, canary: str = "", nonce: str = "",
                       max_chars: int = config.MAX_AGENT_OUTPUT_CHARS) -> OutputResult:
    """Inspect one agent/tool output. Blocks on injection or prompt leakage."""
    if not isinstance(text, str):
        return OutputResult("", True, "Agent output was not text.", ["type_check"])

    # 1. Prompt-leak detection (canary token / per-run nonce must never be echoed).
    if (canary and canary in text) or (nonce and nonce in text):
        return OutputResult("", True, "System prompt leakage detected.", ["prompt_leak_canary"])

    # 2. Indirect injection: scan the *raw* text before we clean it.
    detection: Detection = detect(text)
    if detection.blocked:
        return OutputResult("", True, "Possible injected instructions in agent/tool output.", detection.rules)

    # 3. Neutralise: normalise, strip active content, redact secrets, cap length.
    clean = normalize(text).text
    clean, stripped = strip_active_content(clean)
    clean, redacted = redact_sensitive(clean)
    if len(clean) > max_chars:
        clean = clean[:max_chars].rstrip() + " [truncated]"
        stripped.append("truncated")
    return OutputResult(clean, rules=detection.rules + stripped, redactions=redacted)


REQUIRED_REPORT_MARKERS = (
    "STRATEGIC SUPPLY CHAIN RISK REPORT", "EXECUTIVE SUMMARY", "RECOMMENDED ACTION",
)


def validate_final_report(text: str) -> OutputResult:
    """Last gate before the report reaches a human."""
    res = guard_agent_output(text, max_chars=config.MAX_REPORT_CHARS)
    if res.blocked:
        return res
    missing = [m for m in REQUIRED_REPORT_MARKERS if m not in res.text]
    if missing:
        return OutputResult("", True, f"Report failed structure validation (missing {missing}).", ["schema_check"])
    return res

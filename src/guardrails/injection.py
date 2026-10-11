"""Rule-based prompt-injection detector (direct + indirect).

Scores text against weighted rules. It is intentionally a *cheap first
layer*: it is deterministic, explainable and fast, and is combined with
structural defences (spotlighting, allow-listed tools, action policy) so
that a missed pattern does not become a successful attack.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..config import BLOCK_THRESHOLD
from .sanitizer import normalize


@dataclass(frozen=True)
class Finding:
    rule: str
    weight: int


@dataclass
class Detection:
    findings: list[Finding] = field(default_factory=list)

    @property
    def score(self) -> int:
        return sum(f.weight for f in self.findings)

    @property
    def blocked(self) -> bool:
        return self.score >= BLOCK_THRESHOLD

    @property
    def rules(self) -> list[str]:
        return [f.rule for f in self.findings]


I = re.I | re.S
RULES: list[tuple[str, re.Pattern[str], int]] = [
    ("instruction_override", re.compile(
        r"\b(ignore|disregard|forget|override|bypass|skip)\b.{0,40}\b(previous|prior|above|earlier|all|any|every|system|safety|your)\b"
        r".{0,30}\b(instruction|prompt|rule|guideline|directive|polic|constraint|guardrail)", I), 3),
    ("new_instructions", re.compile(r"\b(new|updated|real|actual) (instructions?|rules?|directives?|task)\b", I), 2),
    ("role_hijack", re.compile(r"\b(you are (now|no longer)|from now on|pretend (to be|you)|act as (an?|the)|roleplay as)\b", I), 3),
    ("prompt_extraction", re.compile(
        r"\b(reveal|show|print|repeat|leak|output|display|tell me|what (is|are))\b.{0,40}"
        r"\b(system prompt|your (instructions|prompt|rules)|developer message|hidden (prompt|instructions)|api[_ -]?key|secret|credential|password|token)", I), 3),
    ("role_marker", re.compile(r"(^|\n)\s*(system|assistant|developer|user)\s*:", I), 3),
    ("chat_template_token", re.compile(r"<\|?\s*(im_start|im_end|system|endoftext|eot_id)\s*\|?>|\[/?(INST|SYS)\]|<<\s*SYS\s*>>", I), 3),
    ("jailbreak_phrase", re.compile(r"\b(jailbreak|do anything now|developer mode|dan mode|no restrictions|without (any )?restrictions)\b", I), 3),
    ("delimiter_break", re.compile(r"(```|</?\s*(untrusted_data|data|context|system|instructions?)\b|-{3,}\s*end)", I), 2),
    ("code_or_shell", re.compile(r"\b(os\.system|subprocess|__import__|eval\(|exec\(|rm -rf|sudo|chmod|powershell|/bin/(ba)?sh)\b|\b(curl|wget)\s", I), 3),
    ("html_or_script", re.compile(r"<\s*(script|iframe|img|svg|object|embed|style|link)\b|javascript:|on(error|load)\s*=", I), 3),
    ("markdown_image_exfil", re.compile(r"!\[[^\]]*\]\([^)]*\)", I), 3),
    ("url", re.compile(r"\b(https?|ftp)://\S+|\bwww\.\S+", I), 1),
    ("exfiltration_intent", re.compile(r"\b(send|post|forward|upload|email|exfiltrate)\b.{0,40}\b(this|the|all|these|your)\b.{0,40}\b(to|at)\b", I), 2),
    ("encoded_payload", re.compile(r"[A-Za-z0-9+/]{40,}={0,2}"), 2),
    ("action_manipulation", re.compile(
        r"\b(approve|authori[sz]e|execute|wire|transfer|pay|purchase|order)\b.{0,40}\b(\d[\d,]{3,}|immediately|without (approval|review|human))", I), 3),
    ("secrecy_request", re.compile(r"\b(do not|don't|never) (tell|inform|mention|notify|alert|log)\b", I), 2),
]

# Obfuscation catch: "i g n o r e  p r e v i o u s" or "ignore_previous-instructions"
COMPACT_KEYWORDS = (
    "ignorepreviousinstructions", "ignoreallprevious", "ignoretheabove", "disregardprevious",
    "disregardallprevious", "forgetpreviousinstructions", "systemprompt", "developermode",
    "jailbreak", "overridesafety", "bypasssafety",
)


def detect(text: str) -> Detection:
    """Scan *text* (after normalisation) and return all findings."""
    report = normalize(text)
    det = Detection()
    if report.removed_tag_chars:
        det.findings.append(Finding("hidden_unicode_tags", 3))      # ASCII smuggling
    elif report.removed_format_chars:
        det.findings.append(Finding("hidden_format_chars", 1))
    for name, pattern, weight in RULES:
        if pattern.search(report.text):
            det.findings.append(Finding(name, weight))
    compact = re.sub(r"[^a-z]", "", report.text.lower())
    if any(k in compact for k in COMPACT_KEYWORDS) and not any(f.weight >= 3 for f in det.findings):
        det.findings.append(Finding("obfuscated_injection", 3))
    return det

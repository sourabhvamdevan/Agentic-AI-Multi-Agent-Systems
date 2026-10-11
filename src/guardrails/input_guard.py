"""Layer 1 - validate and sanitise the user-supplied input."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .. import config
from .injection import detect
from .sanitizer import normalize


@dataclass
class InputResult:
    ok: bool
    clean: str = ""
    reason: str = ""
    rules: list[str] = field(default_factory=list)


def guard_user_input(raw: object) -> InputResult:
    """Return a sanitised region string, or a rejection with the rules that fired."""
    if not isinstance(raw, str):
        return InputResult(False, reason="Input must be text.", rules=["type_check"])

    # Cap *before* heavy processing so huge payloads can't burn CPU/tokens.
    if len(raw) > config.MAX_INPUT_CHARS * 4:
        return InputResult(False, reason="Input is too long.", rules=["length_limit"])

    norm = normalize(raw)
    detection = detect(raw)
    if detection.blocked:
        return InputResult(False, reason="Input rejected: possible prompt injection.", rules=detection.rules)

    text = norm.text
    if not (config.MIN_INPUT_CHARS <= len(text) <= config.MAX_INPUT_CHARS):
        return InputResult(False, reason=f"Input must be {config.MIN_INPUT_CHARS}-{config.MAX_INPUT_CHARS} characters.",
                           rules=["length_limit"])
    if not re.fullmatch(config.ALLOWED_INPUT_REGEX, text):
        return InputResult(False, reason="Input contains characters that are not allowed.", rules=["charset_allowlist"])
    if not re.search(r"[^\W\d_]", text):
        return InputResult(False, reason="Input must contain letters.", rules=["charset_allowlist"])
    return InputResult(True, clean=text, rules=detection.rules)

class GuardrailViolation(Exception):
    """Raised when content is rejected by a guardrail."""

    def __init__(self, reason: str, rules: list[str] | None = None):
        super().__init__(reason)
        self.reason = reason
        self.rules = rules or []


class ToolNotAllowed(GuardrailViolation):
    """Raised when an agent tries to call a tool that is not allow-listed."""

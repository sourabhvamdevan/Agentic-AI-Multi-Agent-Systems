# Security Design and Threat Model

Aligned with the OWASP Top 10 for LLM Applications: **LLM01 Prompt Injection**, **LLM02 Insecure Output Handling**, **LLM06 Sensitive Information Disclosure**, **LLM07 System Prompt Leakage** and **LLM08 Excessive Agency**.

## Assets and trust boundaries

| Source | Trust level |
|---|---|
| Developer-written system prompt and `config.py` | Trusted |
| User input (region name) | **Untrusted** |
| Tool results (news feed, future APIs) | **Untrusted** (possible indirect injection) |
| Output of every agent | **Untrusted** (may carry injected or leaked content) |

## Threats and controls

| Threat | Example | Controls |
|---|---|---|
| Direct prompt injection | "Ignore previous instructions and ..." | L1 charset allow-list and length cap, L2 detector, L3 spotlighting |
| Obfuscated injection | Spaced letters, full-width text, zero-width splits, Unicode tag smuggling | NFKC normalisation, invisible-character stripping, compact-keyword check, tag-char rule |
| Indirect injection | Poisoned news result telling the agent to place an order | L4 scan of tool and agent output, L3 data delimiters, L5 (text cannot create actions) |
| System prompt leakage | Model echoes its instructions | Per-run canary token and nonce checked on every output |
| Data exfiltration | Markdown image or link to an attacker URL carrying data | Markdown images blocked, URLs and HTML stripped from outputs |
| Sensitive data disclosure | API keys or emails appearing in tool output | Secret and email redaction before state, logs and report |
| Excessive agency | Agent recommends a huge or unknown action | Allow-listed action types, quantity caps, SKU validation, mandatory human approval, no execute path |
| Runaway loops / cost | Cyclic agent behaviour | Graph recursion limit, input length cap, output truncation |
| Log injection / leakage | Attack text or secrets written to logs | Audit log stores rule names, SHA-256 prefix and length only |

## Detection model

Each rule has a weight. Scores are summed per text; reaching `BLOCK_THRESHOLD` (default 3) blocks the request or output. Lower scores are logged and the text is neutralised (links, HTML and secrets removed). All thresholds live in `src/config.py`.

## Known limitations

1. Regex rules cannot catch every paraphrase, translation or semantic attack. Treat them as one layer.
2. Homoglyphs beyond what NFKC folds (for example Cyrillic look-alikes) are not mapped.
3. The strict input allow-list suits short region names; widening it needs a matching review of the rules.
4. Agents are simulated by default, so LLM-specific behaviour is exercised only through test stubs.
5. Human approval is flagged in the report. Wiring it into a real approval workflow is left to the integrator.

## Recommended next steps

LLM-based injection classifier as an additional layer, adversarial test corpora (for example from public prompt-injection benchmarks), rate limiting per user, signed audit logs, and sandboxing for any future tool that touches external systems.

# Secure LangGraph Multi-Agent Pipeline

## Architecture and Workflow Documentation

**Document:** `structure.md`\
**System:** Secure, guarded LangGraph multi-agent advisory pipeline\
**Primary concern:** Prevent prompt injection, unsafe tool use, secret
leakage, and uncontrolled agent-driven actions.

------------------------------------------------------------------------

## 1. Executive Overview

This system processes an untrusted region or market-related request
through a guarded LangGraph workflow. Input is validated and screened
before any agent runs. A sequence of specialized agents produces
intermediate results, and each result is scanned before it is passed to
the next agent. The pipeline then converts model-generated
recommendations into constrained, allow-listed actions, validates the
final report, redacts sensitive information, and records a
privacy-conscious audit event.

The design follows **defence in depth**: no single filter is treated as
sufficient. Six independent security layers protect different stages of
the request lifecycle.

### Core design principles

-   Treat user input, tool responses, and model output as untrusted
    data.
-   Separate data from instructions wherever possible.
-   Scan every agent/tool hand-off, not only the initial prompt.
-   Do not let free-form LLM text directly execute actions.
-   Apply deterministic policy checks before any action is accepted.
-   Require human approval for actions that cross configured risk
    thresholds.
-   Log decisions and rule identifiers without storing raw prompts or
    secrets.
-   Fail closed: a rejected or flagged request ends in a safe refusal
    rather than continuing analysis.

------------------------------------------------------------------------

## 2. Problem Statement

Multi-agent systems can amplify prompt-injection risks. An unsafe
instruction may arrive directly from a user, be hidden in retrieved
content or tool output, or be propagated by one agent to another. Even
when agents produce valid-looking text, the final output can expose
secrets, contain unsafe links, or suggest actions outside approved
limits.

The system must preserve useful advisory analysis while ensuring that
untrusted text cannot bypass policy or directly trigger consequential
actions.

------------------------------------------------------------------------

## 3. Requirements

### 3.1 Functional requirements

1.  Validate and normalize the incoming region/request value.
2.  Detect direct injection patterns, obfuscation, invisible characters,
    and suspicious markup.
3.  Refuse requests that fail input checks or exceed the configured
    detection threshold.
4.  Run the Market Analyst, Logistics Coordinator, Inventory Strategist,
    and Executive Orchestrator in sequence.
5.  Scan each agent result and every tool response before downstream
    consumption.
6.  Permit only configured tools, such as the `news_signals` tool.
7.  Convert proposed actions into a structured representation and
    validate them against an action policy.
8.  Redact secrets and strip or validate URLs, HTML, and image-derived
    content in the final output.
9.  Produce an advisory report with human-approval flags where needed.
10. Record stage, decision, triggered rules, and a hash in the audit
    log.

### 3.2 Non-functional requirements

-   **Security:** Layered validation, output scanning, least privilege,
    and fail-closed behavior.
-   **Reliability:** Deterministic policy checks should not depend on an
    LLM's self-assessment.
-   **Auditability:** Security decisions should be traceable by stage
    and rule identifier.
-   **Privacy:** Prefer hash-only audit records; avoid retaining raw
    sensitive content.
-   **Maintainability:** Keep guards, agents, tools, and policy logic as
    separate components.
-   **Extensibility:** New agents and tools must pass through the same
    guarded interfaces.
-   **Bounded execution:** Limit graph recursion, tool access,
    quantities, and execution time.

------------------------------------------------------------------------

## 4. High-Level Architecture

``` mermaid
flowchart TD
    U[Untrusted request: region name] --> IG[InputGuard]
    IG -->|valid and not flagged| GA[Guarded LangGraph agents]
    IG -->|invalid or flagged| SR[SafeRefusal]

    subgraph AG[Guarded agent sequence]
      MA[Market Analyst] --> LC[Logistics Coordinator]
      LC --> IS[Inventory Strategist]
      IS --> EO[Executive Orchestrator]
    end

    NT[news_signals tool<br/>allow-listed, output untrusted] --> SC[Tool-output scanner]
    SC --> MA
    GA --> SC2[Agent-output scanner<br/>after each agent]
    SC2 -->|clean| NEXT[Next agent]
    SC2 -->|flagged| SR

    EO -->|structured proposed actions| APE[Action Policy Engine]
    APE -->|policy violation| SR
    APE --> OG[OutputGuard]
    OG -->|validation failure| SR
    OG -->|valid and redacted| AR[Advisory report + approval flags]

    IG -. stage / decision / rules / hash .-> AL[Hash-only JSONL audit log]
    SC2 -. stage / decision / rules / hash .-> AL
    APE -. stage / decision / rules / hash .-> AL
    OG -. stage / decision / rules / hash .-> AL
```

### Architecture boundaries

  -----------------------------------------------------------------------
  Boundary                Responsibility          Trust level
  ----------------------- ----------------------- -----------------------
  User/request input      Supplies a region or    Untrusted
                          request                 

  InputGuard              Validates and detects   Security control
                          suspicious input        

  Agents                  Analyze and propose     Untrusted output
                          structured results      

  External tools          Supply external signals Untrusted output
                          or retrieved data       

  Action Policy Engine    Enforces deterministic  Trusted policy boundary
                          action constraints      

  OutputGuard             Validates and redacts   Security control
                          report content          

  Audit log               Records minimal         Restricted operational
                          decision metadata       data

  Human reviewer          Approves flagged or     Human control
                          consequential           
                          recommendations         
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 5. Defence-in-Depth: Six Independent Layers

``` mermaid
flowchart TD
    L1["L1 - Input validation<br/>Length cap · Unicode NFKC · invisible-character stripping · charset allow-list"]
    L2["L2 - Injection detection<br/>Weighted rules · obfuscation detection · tag-character smuggling · block threshold"]
    L3["L3 - Spotlighting<br/>Per-run random delimiters · data/instruction separation · canary token"]
    L4["L4 - Agent and tool output guard<br/>Indirect-injection scan · prompt-leak check · URL/HTML/image stripping · secret redaction"]
    L5["L5 - Action policy engine<br/>LLM text never drives actions · allow-list · quantity limits · human-in-the-loop"]
    L6["L6 - Audit and limits<br/>Hash-only JSONL audit log · graph recursion limit · allow-listed tools"]

    L1 --> L2 --> L3 --> L4 --> L5 --> L6
```

### L1. Input validation

-   Enforce a maximum input length.
-   Normalize Unicode using NFKC where appropriate.
-   Remove or reject invisible and control characters according to
    policy.
-   Validate the expected character set and accepted region-name format.
-   Reject malformed or empty values before graph execution.

### L2. Injection detection

-   Apply a weighted set of detection rules.
-   Detect common prompt-injection language and suspicious instruction
    overrides.
-   Identify obfuscation, markup/tag-character smuggling, and unusual
    encodings.
-   Compare the score against a configured block threshold.
-   Treat detection as a gate, not as proof that an input is safe.

### L3. Spotlighting and instruction/data separation

-   Mark user-provided content as data, not trusted instructions.
-   Use per-run delimiters or equivalent structured boundaries.
-   Keep a canary token or equivalent integrity check for detecting
    unexpected prompt leakage.
-   Do not rely on delimiters alone; they complement the other controls.

### L4. Agent and tool output guard

-   Scan every agent output before it is provided to another agent.
-   Scan tool responses for indirect prompt injection and embedded
    instructions.
-   Check for prompt leakage and secret-like values.
-   Strip or safely handle unneeded HTML, URLs, and image-derived
    content.
-   Reject or quarantine suspicious output instead of forwarding it.

### L5. Action policy engine

-   Treat LLM recommendations as proposals, never as executable
    commands.
-   Parse proposals into a typed, structured action schema.
-   Enforce tool/action allow-lists, quantity limits, and approval
    rules.
-   Require human approval for configured high-impact actions.
-   Reject unknown fields, unsupported actions, and values outside
    policy.

### L6. Audit and execution limits

-   Record stage, decision, rule IDs, and a content hash in JSONL
    format.
-   Avoid storing raw prompts, secrets, or full sensitive tool
    responses.
-   Configure a graph recursion limit and per-tool timeouts.
-   Restrict tools to an explicit allow-list.
-   Monitor repeated refusals, policy violations, and abnormal graph
    depth.

------------------------------------------------------------------------

## 6. Component Breakdown

  ------------------------------------------------------------------------------------
  Component                 Responsibility    Input             Output
  ------------------------- ----------------- ----------------- ----------------------
  `InputGuard`              Normalize,        Raw request       Validated request or
                            validate, and                       refusal
                            detect direct                       
                            injection                           

  `SpotlightingPolicy`      Preserve the      Validated request Delimited/structured
                            boundary between                    context
                            instructions and                    
                            untrusted data                      

  `MarketAnalyst`           Analyze market    Guarded context   Market findings
                            signals           and approved      
                                              signals           

  `LogisticsCoordinator`    Assess logistics  Scanned market    Logistics findings
                            implications      findings          

  `InventoryStrategist`     Develop inventory Scanned upstream  Inventory proposal
                            recommendations   findings          

  `ExecutiveOrchestrator`   Combine findings  Scanned findings  Report draft and
                            into a structured                   proposed actions
                            advisory proposal                   

  `NewsSignalsTool`         Retrieve approved Constrained query Untrusted tool result
                            external signals                    

  `AgentOutputGuard`        Scan intermediate Agent or tool     Clean result or
                            agent/tool output result            flagged result

  `ActionPolicyEngine`      Enforce action    Structured        Accepted actions or
                            allow-list,       proposal          policy rejection
                            quantity, and                       
                            approval rules                      

  `OutputGuard`             Validate report   Proposed report   Safe report or refusal
                            structure and                       
                            redact secrets                      

  `AuditLogger`             Record minimal    Stage decision    Hash-only JSONL event
                            security event    and rule IDs      
                            metadata                            

  `SafeRefusal`             Stop unsafe       Refusal reason    Safe refusal response
                            execution without code              
                            returning                           
                            analysis                            
  ------------------------------------------------------------------------------------

> These are logical component names. Map them to the actual Python
> modules and LangGraph node names used by the implementation.

------------------------------------------------------------------------

## 7. Suggested Package / Folder Structure

``` text
secure-langgraph-pipeline/
├── README.md
├── structure.md
├── pyproject.toml
├── .env.example
├── src/
│   └── secure_pipeline/
│       ├── __init__.py
│       ├── graph.py
│       ├── state.py
│       ├── config.py
│       ├── guards/
│       │   ├── __init__.py
│       │   ├── input_guard.py
│       │   ├── injection_detector.py
│       │   ├── spotlighting.py
│       │   ├── agent_output_guard.py
│       │   └── output_guard.py
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── market_analyst.py
│       │   ├── logistics_coordinator.py
│       │   ├── inventory_strategist.py
│       │   └── executive_orchestrator.py
│       ├── tools/
│       │   ├── __init__.py
│       │   └── news_signals.py
│       ├── policies/
│       │   ├── __init__.py
│       │   └── action_policy_engine.py
│       ├── audit/
│       │   ├── __init__.py
│       │   └── audit_logger.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── request.py
│       │   ├── agent_result.py
│       │   ├── proposed_action.py
│       │   └── advisory_report.py
│       └── errors.py
└── tests/
    ├── test_input_guard.py
    ├── test_injection_detector.py
    ├── test_agent_output_guard.py
    ├── test_action_policy_engine.py
    ├── test_output_guard.py
    ├── test_graph_refusal_paths.py
    └── test_audit_logger.py
```

The structure is a recommended mapping, not a claim about files already
present in the repository.

------------------------------------------------------------------------

## 8. LangGraph State Model

Keep graph state explicit and typed. Pass only the minimum information
each node needs.

``` python
from typing import Any, Literal, TypedDict

class PipelineState(TypedDict, total=False):
    request_id: str
    raw_input: str
    normalized_input: str
    input_status: Literal["pending", "accepted", "rejected"]
    current_stage: str
    agent_results: dict[str, Any]
    tool_results: dict[str, Any]
    proposed_actions: list[dict[str, Any]]
    report_draft: dict[str, Any]
    approval_flags: list[str]
    triggered_rules: list[str]
    refusal_reason: str
    final_report: dict[str, Any]
```

### State handling rules

-   Do not store secrets or unnecessary raw tool output in long-lived
    state.
-   Use explicit status values and schema validation for transitions.
-   Never interpret free-form agent text as a policy decision.
-   Ensure a rejected state cannot route back into the analysis path.
-   Keep audit metadata separate from user-visible report content.

------------------------------------------------------------------------

## 9. End-to-End Workflow

``` mermaid
sequenceDiagram
    actor User
    participant IG as InputGuard
    participant SD as Injection Detector
    participant LG as LangGraph Agents
    participant TG as Tool Guard
    participant AP as Action Policy Engine
    participant OG as OutputGuard
    participant AL as AuditLogger
    actor Human as Human Reviewer

    User->>IG: Submit region/request
    IG->>SD: Normalized input
    SD->>AL: Log stage, decision, rules, hash
    alt Input invalid or injection threshold exceeded
        SD-->>User: SafeRefusal
    else Input accepted
        IG->>LG: Guarded request
        loop Each agent in sequence
            LG->>TG: Agent result or tool result
            TG->>AL: Log scan decision and hash
            alt Output flagged
                TG-->>User: SafeRefusal
            else Output clean
                TG-->>LG: Scanned result for next node
            end
        end
        LG->>AP: Structured proposed actions
        AP->>AL: Log policy decision
        alt Policy violation
            AP-->>User: SafeRefusal
        else Policy accepted
            AP->>OG: Draft report and approved action set
            OG->>AL: Log output validation decision
            alt Output validation fails
                OG-->>User: SafeRefusal
            else Output valid
                OG-->>User: Advisory report and approval flags
                opt Approval required
                    User->>Human: Route recommendation for review
                end
            end
        end
    end
```

### Workflow steps

1.  **Receive request:** Accept a region name or other explicitly
    supported request field.
2.  **Validate input:** Enforce length, normalization, character, and
    format constraints.
3.  **Detect injection:** Run weighted rules and block if the configured
    threshold is exceeded.
4.  **Establish data boundaries:** Mark accepted user content as
    untrusted data inside the model context.
5.  **Run Market Analyst:** Analyze allowed market signals; scan the
    result before continuing.
6.  **Run Logistics Coordinator:** Consume only the scanned upstream
    result; scan its output.
7.  **Run Inventory Strategist:** Build inventory recommendations from
    scanned findings; scan its output.
8.  **Run Executive Orchestrator:** Produce a report draft and
    structured proposed actions; scan the result.
9.  **Enforce action policy:** Validate every proposed action against
    schemas, allow-lists, limits, and approval rules.
10. **Validate final output:** Check report structure, remove secrets,
    and sanitize links or markup.
11. **Return or refuse:** Return a safe advisory report with approval
    flags, or stop with a safe refusal.
12. **Audit:** Record minimal metadata at each security boundary.

------------------------------------------------------------------------

## 10. Request Flow: Allowed vs. Blocked Paths

``` mermaid
flowchart TD
    R[Request] --> IV{Input passes validation<br/>and detection?}
    IV -->|No| REF[SafeRefusal<br/>no analysis; event logged]
    IV -->|Yes| AG[Run agents in sequence<br/>scan each output before next agent]
    AG --> FL{Any agent/tool output<br/>flagged?}
    FL -->|Yes| REF
    FL -->|No| PE[Action Policy Engine<br/>convert proposal to allow-listed actions]
    PE -->|Policy violation| REF
    PE -->|Accepted| OG[OutputGuard<br/>validate and redact report]
    OG -->|Validation fails| REF
    OG -->|Valid| OUT[Advisory report<br/>with approval flags]
    R -.-> AUD[Audit log: stage · decision · rules · hash]
    IV -.-> AUD
    FL -.-> AUD
    PE -.-> AUD
    OG -.-> AUD
```

### Allowed path

A request is accepted, all intermediate outputs pass their guards,
proposed actions satisfy deterministic policy, and the final report
passes validation. The user receives an advisory report, including
human-approval flags when applicable.

### Blocked path

A failed input check, flagged intermediate output, action-policy
violation, or failed final-output check stops the analysis path. The
system returns a safe refusal and records a minimal audit event. No
rejected result should be passed to another agent.

------------------------------------------------------------------------

## 11. Agent and Tool Guarding Rules

### Sequential agent chain

``` mermaid
flowchart TD
    IN[Guarded request] --> MA[Market Analyst]
    MA --> G1{Output guard}
    G1 -->|Clean| LC[Logistics Coordinator]
    G1 -->|Flagged| SR[SafeRefusal]
    LC --> G2{Output guard}
    G2 -->|Clean| IS[Inventory Strategist]
    G2 -->|Flagged| SR
    IS --> G3{Output guard}
    G3 -->|Clean| EO[Executive Orchestrator]
    G3 -->|Flagged| SR
    EO --> G4{Output guard}
    G4 -->|Clean| AP[Action Policy Engine]
    G4 -->|Flagged| SR
```

### Tool policy

-   Only explicitly allow-listed tools may be invoked.
-   Tool arguments must be validated and bounded before invocation.
-   Tool output is untrusted even when it comes from an approved tool.
-   Retrieved content must not be allowed to modify system policy or
    agent roles.
-   Apply timeouts, response-size limits, and error handling to every
    external tool.
-   A tool failure must not silently produce fabricated data or bypass a
    guard.

------------------------------------------------------------------------

## 12. Action Policy Engine

The Action Policy Engine is the boundary between analysis and
consequential operations.

### Validation pipeline

``` mermaid
flowchart LR
    P[Agent proposal] --> S[Schema validation]
    S --> A[Action allow-list]
    A --> Q[Quantity and range limits]
    Q --> H{Human approval required?}
    H -->|Yes| WAIT[Mark pending approval]
    H -->|No| ACCEPT[Accepted advisory action]
    S -->|Invalid| REJECT[Reject proposal]
    A -->|Not allowed| REJECT
    Q -->|Out of range| REJECT
```

### Policy requirements

-   Accept only known action types and fields.
-   Reject malformed, unknown, or over-limit actions.
-   Use deterministic code for limits and approval rules.
-   Keep approval status separate from model-generated claims.
-   The LLM may recommend an action but cannot grant itself permission.
-   If the implementation executes real-world actions, require an
    explicit authorization mechanism outside the model response.

------------------------------------------------------------------------

## 13. Audit Logging and Observability

### Suggested event schema

``` json
{
  "request_id": "opaque-request-id",
  "stage": "agent_output_guard",
  "decision": "blocked",
  "rule_ids": ["INDIRECT_INJECTION_03"],
  "content_hash": "sha256:...",
  "timestamp": "ISO-8601 timestamp"
}
```

This is an illustrative schema. Use a cryptographically secure hash and
avoid logging raw input, model prompts, secrets, or full tool responses
by default.

### Operational metrics

-   Requests accepted and refused by stage.
-   Injection detector scores and rule hit counts, without raw payload
    retention.
-   Agent/tool guard rejection rate.
-   Tool latency, timeout rate, and response-size distribution.
-   Action-policy rejection and approval-pending counts.
-   Output redaction counts.
-   Graph recursion-limit and unexpected-error events.

Audit data should have access controls, retention limits, and integrity
protections. A hash can help correlate or verify content but does not,
by itself, guarantee anonymity or tamper-proof logging.

------------------------------------------------------------------------

## 14. Error Handling and State Transitions

``` mermaid
stateDiagram-v2
    [*] --> Received
    Received --> Validating
    Validating --> Rejected: Invalid input / injection threshold
    Validating --> RunningAgents: Accepted
    RunningAgents --> Rejected: Agent/tool output flagged
    RunningAgents --> PolicyCheck: All outputs clean
    PolicyCheck --> Rejected: Action violates policy
    PolicyCheck --> OutputValidation: Policy accepted
    OutputValidation --> Rejected: Invalid output / secret leak
    OutputValidation --> ApprovalPending: Human review required
    OutputValidation --> Completed: No approval required
    ApprovalPending --> Completed: Approved
    ApprovalPending --> Rejected: Denied
    Completed --> [*]
    Rejected --> [*]
```

### State transition invariants

-   `Rejected` is terminal for the current request.
-   No agent executes after a refusal decision.
-   Only validated structured actions reach the policy engine.
-   Only output-guard-approved reports reach the user.
-   Approval-pending recommendations must not be represented as
    completed actions.

------------------------------------------------------------------------

## 15. Class / Component Diagram

``` mermaid
classDiagram
    class InputGuard {
      +validate(raw_input)
      +normalize(raw_input)
    }
    class InjectionDetector {
      +score(text)
      +should_block(score)
    }
    class SpotlightingPolicy {
      +wrap_untrusted_data(text)
      +verify_canary(context)
    }
    class AgentOutputGuard {
      +scan_agent_output(agent_name, output)
      +scan_tool_output(tool_name, output)
    }
    class MarketAnalyst {
      +analyze(state)
    }
    class LogisticsCoordinator {
      +coordinate(state)
    }
    class InventoryStrategist {
      +recommend(state)
    }
    class ExecutiveOrchestrator {
      +build_proposal(state)
    }
    class ActionPolicyEngine {
      +validate_schema(proposal)
      +enforce_allow_list(proposal)
      +enforce_limits(proposal)
      +requires_approval(proposal)
    }
    class OutputGuard {
      +validate_report(report)
      +redact_secrets(report)
      +sanitize_links(report)
    }
    class AuditLogger {
      +record_event(stage, decision, rules, hash)
    }
    class SafeRefusal {
      +build_response(reason_code)
    }

    InputGuard --> InjectionDetector
    InputGuard --> SpotlightingPolicy
    MarketAnalyst --> AgentOutputGuard
    LogisticsCoordinator --> AgentOutputGuard
    InventoryStrategist --> AgentOutputGuard
    ExecutiveOrchestrator --> AgentOutputGuard
    ActionPolicyEngine --> AuditLogger
    InputGuard --> AuditLogger
    AgentOutputGuard --> AuditLogger
    OutputGuard --> AuditLogger
    ActionPolicyEngine --> OutputGuard
    InputGuard ..> SafeRefusal
    AgentOutputGuard ..> SafeRefusal
    ActionPolicyEngine ..> SafeRefusal
    OutputGuard ..> SafeRefusal
```

------------------------------------------------------------------------

## 16. Design Pattern Analysis

  -----------------------------------------------------------------------
  Pattern                 Application             Benefit
  ----------------------- ----------------------- -----------------------
  Chain of Responsibility Sequential guards and   Every stage can accept,
                          agent-output checks     reject, or pass a
                                                  result onward

  Strategy                Replaceable injection   Detection logic can
                          detection rules or      evolve without changing
                          risk-scoring strategies graph orchestration

  State                   Explicit request status Prevents invalid
                          and terminal refusal    transitions and
                          state                   accidental continuation

  Adapter                 Wrap external news or   Isolates
                          signal providers behind provider-specific
                          a constrained tool      behavior and normalizes
                          interface               output

  Policy Object           Centralized action      Keeps authorization
                          allow-list, limits, and deterministic and
                          approval rules          testable

  Observer / Event        Emit audit events at    Improves traceability
  logging                 security boundaries     without coupling the
                                                  graph to storage
                                                  details

  Pipeline                Input, agent, action,   Makes the order of
                          and output processing   security checks
                          stages                  explicit
  -----------------------------------------------------------------------

Patterns should support the actual implementation rather than be added
solely for naming purposes.

------------------------------------------------------------------------

## 17. SOLID Principles

-   **Single Responsibility:** Input validation, injection detection,
    action policy, output sanitation, and audit logging remain separate
    responsibilities.
-   **Open/Closed:** New detection rules and agent implementations can
    be added through stable interfaces without weakening existing
    controls.
-   **Liskov Substitution:** Alternative guard or tool implementations
    must preserve the same acceptance, rejection, and error semantics.
-   **Interface Segregation:** Agents should receive only the state and
    tool interfaces they require.
-   **Dependency Inversion:** Graph orchestration should depend on
    guard, policy, and tool interfaces rather than provider-specific
    implementations.

------------------------------------------------------------------------

## 18. Security Threats and Mitigations

  -----------------------------------------------------------------------
  Threat                  Mitigation              Residual consideration
  ----------------------- ----------------------- -----------------------
  Direct prompt injection Input normalization and Detection can miss
                          weighted detection      novel phrasing

  Indirect injection in   Scan tool results and   Scanner quality must be
  retrieved data          agent outputs           tested continuously

  Instruction/data        Spotlighting and        Delimiters are not a
  confusion               structured context      security boundary by
                          boundaries              themselves

  Prompt or secret        Prompt-leak checks,     Secret detection can
  leakage                 secret redaction,       have false positives
                          minimal logging         and false negatives

  Unauthorized tool call  Tool allow-list and     Tool credentials must
                          argument validation     also be least-privilege

  Unsafe action proposal  Structured schema and   Policy must reflect
                          deterministic policy    real operational risk
                          engine                  

  Excessive tool/agent    Graph recursion cap,    Tune limits to avoid
  recursion               timeouts, response      disrupting valid
                          limits                  workloads

  Malicious HTML or URLs  Strip, validate, or     Avoid rendering
                          safely render output    untrusted HTML directly

  Audit data exposure     Hash-only/minimal       Hashes may still be
                          events, access          linkable and are not
                          controls, retention     anonymization
                          policy                  guarantees

  Guard bypass through    Fail-closed routing and Test every exception
  errors                  explicit error states   and timeout path
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 19. Testing Strategy

### Unit tests

-   Input length, Unicode normalization, invisible characters, and
    allowed character set.
-   Injection rule scoring, threshold boundaries, and obfuscation cases.
-   Spotlighting boundaries and canary integrity checks.
-   Agent-output and tool-output scan decisions.
-   Action schema validation, allow-list enforcement, quantity bounds,
    and approval rules.
-   Secret redaction, URL sanitation, and report schema validation.
-   Audit event content, ensuring raw prompts and secrets are not
    written.

### Integration tests

-   Valid input traverses every agent in the intended order.
-   Flagged output stops the graph before the next agent runs.
-   Tool responses are scanned before an agent consumes them.
-   Policy violations cannot reach the output stage as accepted actions.
-   OutputGuard failures return a refusal.
-   Audit events are emitted for both allowed and blocked paths.
-   Recursion and timeout limits fail safely.

### Adversarial tests

Include direct and indirect injection, mixed Unicode, invisible
characters, tag/markup smuggling, encoded payloads, tool-output attacks,
prompt-leak attempts, secret-like strings, malformed action objects,
excessive quantities, and attempts to invoke non-allow-listed tools.

Measure false positives and false negatives. Do not treat a successful
test suite as proof that prompt injection has been eliminated.

------------------------------------------------------------------------

## 20. Scalability and Reliability Considerations

-   Keep guard interfaces stateless where practical so they can be
    scaled independently.
-   Cache only safe, non-sensitive, versioned reference data. Do not
    reuse per-run security delimiters or canary values across requests
    if uniqueness is part of the design.
-   Use bounded concurrency for independent read-only tool calls, while
    preserving required agent dependencies.
-   Apply timeouts, retry limits, circuit breakers, and response-size
    limits to external tools.
-   Make audit delivery resilient, but do not let audit failures
    silently disable security checks. Define whether the request must
    fail closed when mandatory audit storage is unavailable.
-   Version detection rules and action policies so decisions can be
    reproduced.
-   Track guard latency and refusal rates to identify performance
    regressions or rule drift.
-   Keep the action-policy engine deterministic and separate from model
    inference.

------------------------------------------------------------------------

## 21. Future Enhancements

1.  Add a versioned policy registry with change review and rollback.
2.  Add a human-approval queue with identity, timestamp, decision, and
    reason.
3.  Introduce structured schemas for every agent output and tool
    response.
4.  Add automated adversarial regression suites for prompt injection and
    data exfiltration.
5.  Add trace IDs across graph nodes while avoiding sensitive payload
    logging.
6.  Add risk-tiered approval rules for different classes of proposed
    actions.
7.  Add monitoring dashboards for guard latency, blocked paths, tool
    errors, and approval backlog.
8.  Add threat-model reviews whenever a new agent, tool, or data source
    is introduced.

------------------------------------------------------------------------

## 22. Learning Outcomes

-   Understand defence in depth for LLM and multi-agent applications.
-   Design guarded LangGraph workflows with explicit state transitions.
-   Separate untrusted data from trusted instructions.
-   Secure agent-to-agent and tool-to-agent hand-offs.
-   Use deterministic policy enforcement for proposed actions.
-   Build privacy-conscious audit logs and bounded graph execution.
-   Test failure paths and adversarial inputs, not only successful
    requests.

------------------------------------------------------------------------

## 23. Implementation Checklist

-   [ ] Input length, normalization, and character policy implemented.
-   [ ] Injection detector rules and blocking threshold configured.
-   [ ] Untrusted user and retrieved content clearly separated from
    trusted instructions.
-   [ ] Every agent output is scanned before the next agent consumes it.
-   [ ] Every tool response is scanned before downstream use.
-   [ ] Only allow-listed tools can be invoked.
-   [ ] Agent outputs use validated structured schemas.
-   [ ] Action policy enforces allow-lists, quantity limits, and
    approval requirements.
-   [ ] OutputGuard validates the report and redacts secrets.
-   [ ] Refusal paths are terminal and fail closed.
-   [ ] Graph recursion, tool timeout, and response-size limits are
    configured.
-   [ ] Audit events omit raw prompts and secrets.
-   [ ] Unit, integration, and adversarial tests cover allowed and
    blocked paths.
-   [ ] Actual source file names and class names are aligned with this
    document.

------------------------------------------------------------------------

## 24. Final Summary

The pipeline is organized around one central rule: **model output is
advisory, not authority**. Each request is validated before analysis,
every intermediate result is treated as untrusted, proposed actions are
constrained by deterministic policy, and the final report is validated
before delivery. Independent controls, terminal refusal paths, human
approval, and minimal audit records reduce the chance that one failed
safeguard compromises the entire workflow.

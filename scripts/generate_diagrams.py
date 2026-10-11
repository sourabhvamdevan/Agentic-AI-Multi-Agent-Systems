"""Regenerate the README diagrams.  Requires: pip install graphviz  +  Graphviz `dot` binary.

    python scripts/generate_diagrams.py
"""
from pathlib import Path

from graphviz import Digraph

OUT = Path(__file__).resolve().parents[1] / "images"
OUT.mkdir(exist_ok=True)

FONT = "Helvetica"
C = dict(guard="#FDE8E8", guard_b="#C0392B", agent="#E8F0FE", agent_b="#2F5FBF",
         data="#FFF8E1", data_b="#B8860B", ok="#E6F4EA", ok_b="#1E7B3A", ink="#1F2937")


def base(name, rankdir="LR", **kw) -> Digraph:
    g = Digraph(name, format="png")
    g.attr(rankdir=rankdir, bgcolor="white", fontname=FONT, pad="0.4", dpi="170", nodesep="0.45", ranksep="0.6", **kw)
    g.attr("node", fontname=FONT, fontsize="12", style="filled,rounded", shape="box", color=C["ink"],
           fontcolor=C["ink"], penwidth="1.4", margin="0.2,0.12")
    g.attr("edge", fontname=FONT, fontsize="10", color="#4B5563", fontcolor="#4B5563", penwidth="1.3")
    return g


def guard(g, n, label): g.node(n, label, fillcolor=C["guard"], color=C["guard_b"])
def agent(g, n, label): g.node(n, label, fillcolor=C["agent"], color=C["agent_b"])
def data(g, n, label): g.node(n, label, fillcolor=C["data"], color=C["data_b"])
def good(g, n, label): g.node(n, label, fillcolor=C["ok"], color=C["ok_b"])


# 1 ─ architecture ───────────────────────────────────────────────────────────
def architecture():
    g = base("architecture", "TB", label="Secure LangGraph pipeline - every hop is guarded",
             labelloc="t", fontsize="18", compound="true")
    data(g, "user", "Untrusted input (region name)")
    guard(g, "ig", "InputGuard\nvalidate · normalise · detect injection")

    with g.subgraph(name="cluster_agents") as c:
        c.attr(label="Guarded agents - each output is scanned before the next agent sees it",
               style="rounded,dashed", color=C["agent_b"], fontname=FONT, fontsize="11", fontcolor=C["agent_b"])
        c.attr("node", style="filled,rounded", fontname=FONT, fontsize="12", color=C["agent_b"], fillcolor=C["agent"])
        c.node("ma", "Market Analyst")
        c.node("lc", "Logistics Coordinator")
        c.node("is", "Inventory Strategist")
        c.node("eo", "Executive Orchestrator")
        c.edge("ma", "lc"); c.edge("lc", "is"); c.edge("is", "eo")

    guard(g, "pe", "Action Policy Engine\nallow-list · quantity limits · approval rules")
    guard(g, "og", "OutputGuard\nredact secrets · strip links · validate report")
    good(g, "rep", "Advisory report + human-approval flags")
    guard(g, "sr", "SafeRefusal\n(no analysis returned)")
    data(g, "tool", "news_signals tool\n(allow-listed · output untrusted)")

    g.edge("user", "ig")
    g.edge("ig", "ma", lhead="cluster_agents")
    g.edge("eo", "pe", ltail="cluster_agents", label="  structured actions")
    g.edge("pe", "og"); g.edge("og", "rep")
    g.edge("tool", "ma", style="dashed", label=" scanned ")
    g.edge("ig", "sr", style="dashed", color=C["guard_b"], fontcolor=C["guard_b"], label=" blocked", constraint="false")
    g.edge("lc", "sr", style="dashed", color=C["guard_b"], fontcolor=C["guard_b"],
           label=" flagged output", ltail="cluster_agents", constraint="false")
    g.edge("og", "sr", style="dashed", color=C["guard_b"], fontcolor=C["guard_b"], label=" fails", constraint="false")
    g.render(str(OUT / "architecture"), cleanup=True)


# 2 ─ defense layers ─────────────────────────────────────────────────────────
def layers():
    g = base("layers", "TB", label="Defence-in-depth: six independent layers", labelloc="t", fontsize="18")
    g.attr("node", shape="box", width="7.2", fontsize="13")
    rows = [
        ("L1", "Input validation", "length cap · Unicode NFKC · invisible-char stripping · charset allow-list", C["guard"], C["guard_b"]),
        ("L2", "Injection detection", "16 weighted rules · obfuscation catch · tag-char smuggling · block threshold", C["guard"], C["guard_b"]),
        ("L3", "Spotlighting", "per-run random delimiters · data/instruction separation · canary token", C["agent"], C["agent_b"]),
        ("L4", "Agent & tool output guard", "indirect-injection scan · prompt-leak check · URL/HTML/image stripping · secret redaction", C["agent"], C["agent_b"]),
        ("L5", "Action policy engine", "LLM text never drives actions · allow-list · quantity limits · human-in-the-loop", C["data"], C["data_b"]),
        ("L6", "Audit & limits", "hash-only JSONL audit log · graph recursion limit · allow-listed tools", C["ok"], C["ok_b"]),
    ]
    prev = None
    for k, title, desc, fill, line in rows:
        g.node(k, f"{k}  {title}\n{desc}", fillcolor=fill, color=line)
        if prev:
            g.edge(prev, k, arrowhead="vee")
        prev = k
    g.render(str(OUT / "defense_layers"), cleanup=True)


# 3 ─ request flow ───────────────────────────────────────────────────────────
def flow():
    g = base("flow", "TB", label="Request flow: allowed vs. blocked paths", labelloc="t", fontsize="18")
    data(g, "req", "Request")
    g.node("d1", "Input passes\nvalidation + detection?", shape="diamond", fillcolor=C["guard"], color=C["guard_b"],
           margin="0.05,0.05")
    agent(g, "pipe", "Agents run in sequence\n(each output scanned before next agent)")
    g.node("d2", "Any agent / tool output\nflagged?", shape="diamond", fillcolor=C["guard"], color=C["guard_b"],
           margin="0.05,0.05")
    agent(g, "pol", "Policy engine turns numbers\ninto allow-listed actions")
    guard(g, "og", "OutputGuard validates\nand redacts report")
    good(g, "ok", "Advisory report\n(+ approval flags)")
    guard(g, "no", "SafeRefusal\n(no analysis, event logged)")
    data(g, "log", "Audit log: stage · decision · rules · hash")

    g.edge("req", "d1")
    g.edge("d1", "pipe", label=" yes", color=C["ok_b"], fontcolor=C["ok_b"])
    g.edge("d1", "no", label=" no", color=C["guard_b"], fontcolor=C["guard_b"])
    g.edge("pipe", "d2")
    g.edge("d2", "pol", label=" no", color=C["ok_b"], fontcolor=C["ok_b"])
    g.edge("d2", "no", label=" yes", color=C["guard_b"], fontcolor=C["guard_b"])
    g.edge("pol", "og")
    g.edge("og", "ok")
    g.edge("og", "no", label=" fails", color=C["guard_b"], fontcolor=C["guard_b"], constraint="false")
    for n in ("d1", "d2", "og"):
        g.edge(n, "log", style="dotted", arrowhead="none", constraint="false")
    g.render(str(OUT / "request_flow"), cleanup=True)


if __name__ == "__main__":
    architecture(); layers(); flow()
    print("Diagrams written to", OUT)

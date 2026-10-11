"""CLI entry point.  Usage:  python main.py --region "South China Sea" [--json]"""
import argparse
import json
import sys

from src.graph import run


def main() -> int:
    p = argparse.ArgumentParser(description="Secure multi-agent supply chain risk intelligence")
    p.add_argument("--region", default="South China Sea Logistics", help="Region / corridor to analyse")
    p.add_argument("--json", action="store_true", help="Print machine-readable output")
    args = p.parse_args()

    state = run(args.region)
    blocked = bool(state.get("blocked"))

    if args.json:
        print(json.dumps({k: state.get(k) for k in
                          ("blocked", "block_reason", "actions", "requires_human_approval", "final_recommendation")},
                         indent=2))
    else:
        print(f"--- SECURE RISK INTELLIGENCE: {args.region[:80]!r} ---")
        print("=" * 60)
        print(state["final_recommendation"])
        print("=" * 60)
        print("Security events:", ", ".join(f"{e['stage']}={e['decision']}" for e in state["security_events"]))
        if state.get("requires_human_approval"):
            print("NOTE: one or more recommended actions require human approval.")
    return 2 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())

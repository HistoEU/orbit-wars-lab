from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.orbitlab.tournament import run_match


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one authoritative Orbit Wars match.")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--agents", nargs="+", required=True)
    parser.add_argument("--matchup", default="manual")
    args = parser.parse_args()
    result = run_match(seed=args.seed, agents=args.agents, player_count=len(args.agents), debug=True, matchup=args.matchup)
    result.pop("turn_metrics", None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

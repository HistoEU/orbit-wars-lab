from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.orbitlab.pvp import build_pvp_config
from src.orbitlab.scheduler import run_tournament_from_config
from tools import analyze_run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run explicit 2P or 4P Orbit Wars PvP matches.")
    parser.add_argument("--agents", nargs="+", required=True)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    parser.add_argument("--player-count", type=int, default=None, choices=[2, 4])
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--out", default=None)
    parser.add_argument("--viewer-replays", action="store_true")
    parser.add_argument("--focus-agent", default=None)
    args = parser.parse_args(argv)

    config = build_pvp_config(
        agents=args.agents,
        seeds=args.seeds,
        player_count=args.player_count,
        workers=args.workers,
        export_viewer_replays=args.viewer_replays,
    )
    run_dir = run_tournament_from_config(config, out_dir=args.out)
    if args.focus_agent:
        analyze_run.main([run_dir, "--focus-agent", args.focus_agent])
    else:
        analyze_run.main([run_dir])
    print(run_dir)


if __name__ == "__main__":
    main()

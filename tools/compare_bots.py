from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.orbitlab.bot_compare import build_compare_config
from src.orbitlab.scheduler import run_tournament_from_config
from tools import analyze_run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run a candidate-vs-baseline Orbit Wars bot comparison.")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--out", default=None)
    parser.add_argument("--viewer-replays", action="store_true")
    args = parser.parse_args(argv)

    config = build_compare_config(
        candidate=args.candidate,
        baseline=args.baseline,
        seeds=args.seeds,
        workers=args.workers,
        export_viewer_replays=args.viewer_replays,
    )
    run_dir = run_tournament_from_config(config, out_dir=args.out)
    analyze_run.main([run_dir, "--focus-agent", args.candidate])
    print(run_dir)


if __name__ == "__main__":
    main()

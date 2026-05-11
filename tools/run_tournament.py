from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.orbitlab.scheduler import run_tournament_from_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a rotated Orbit Wars tournament.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    run_dir = run_tournament_from_config(config, out_dir=args.out)
    print(run_dir)


if __name__ == "__main__":
    main()

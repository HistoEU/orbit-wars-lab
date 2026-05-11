from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract coarse metrics from a Kaggle replay JSON file.")
    parser.add_argument("replay", nargs="?")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    if not args.replay:
        parser.print_help()
        return
    replay_path = Path(args.replay)
    data = json.loads(replay_path.read_text(encoding="utf-8"))
    steps = data.get("steps", [])
    summary = {"replay": str(replay_path), "steps": len(steps)}
    text = json.dumps(summary, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

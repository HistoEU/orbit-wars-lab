from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def _run(command: list[str]) -> int:
    completed = subprocess.run(command, check=False)
    return completed.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Kaggle Orbit Wars episodes, replays, and logs.")
    parser.add_argument("--submission-id", required=True)
    parser.add_argument("--episodes", nargs="*", default=[])
    parser.add_argument("--agent-index", type=int, default=0)
    parser.add_argument("--out", default=None)
    parser.add_argument("--list-only", action="store_true")
    args = parser.parse_args()

    kaggle = str(Path("kaggle.ps1"))
    if args.list_only or not args.episodes:
        raise SystemExit(_run(["powershell", "-ExecutionPolicy", "Bypass", "-File", kaggle, "competitions", "episodes", args.submission_id, "-v"]))

    out = Path(args.out or f"runs/leaderboard/{args.submission_id}")
    replay_dir = out / "replays"
    log_dir = out / "logs"
    replay_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    exit_code = 0
    for episode in args.episodes:
        exit_code |= _run(["powershell", "-ExecutionPolicy", "Bypass", "-File", kaggle, "competitions", "replay", episode, "-p", str(replay_dir)])
        exit_code |= _run(["powershell", "-ExecutionPolicy", "Bypass", "-File", kaggle, "competitions", "logs", episode, str(args.agent_index), "-p", str(log_dir)])
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.orbitlab.analytics import build_leaderboard, compare_agent_summaries
from src.orbitlab.storage import write_csv


def _read_csv(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _summary_rows(run_dir: Path) -> list[dict]:
    leaderboard = _read_csv(run_dir / "leaderboard.csv")
    if leaderboard:
        return leaderboard
    matches = _read_csv(run_dir / "matches.csv")
    return build_leaderboard(matches)


def compare_run_dirs(baseline_dir: str | Path, candidate_dir: str | Path, out_path: str | Path | None = None) -> Path:
    baseline_dir = Path(baseline_dir)
    candidate_dir = Path(candidate_dir)
    out = Path(out_path) if out_path is not None else candidate_dir / "compare_vs_baseline.csv"
    rows = compare_agent_summaries(_summary_rows(baseline_dir), _summary_rows(candidate_dir))
    write_csv(out, rows)
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare candidate run leaderboard metrics against a baseline run.")
    parser.add_argument("baseline_run_dir")
    parser.add_argument("candidate_run_dir")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    out_path = compare_run_dirs(args.baseline_run_dir, args.candidate_run_dir, args.out)
    print(out_path)


if __name__ == "__main__":
    main()

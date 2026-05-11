from __future__ import annotations

import csv
from pathlib import Path


def _write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_analyze_run_writes_analytics_artifacts(tmp_path: Path):
    from tools import analyze_run

    run_dir = tmp_path / "run"
    _write_csv(
        run_dir / "matches.csv",
        [
            {
                "match_id": "m1",
                "matchup": "candidate_vs_baseline",
                "agents": "['candidate', 'baseline']",
                "rewards": "[1, -1]",
                "statuses": "['DONE', 'DONE']",
                "steps": "240",
                "winner_agent": "candidate",
                "elapsed_seconds": "0.25",
            },
            {
                "match_id": "m2",
                "matchup": "candidate_vs_baseline",
                "agents": "['baseline', 'candidate']",
                "rewards": "[1, -1]",
                "statuses": "['DONE', 'ERROR']",
                "steps": "120",
                "winner_agent": "baseline",
                "elapsed_seconds": "0.30",
            },
        ],
    )
    _write_csv(
        run_dir / "turn_metrics.csv",
        [
            {
                "match_id": "m1",
                "step": "20",
                "slot": "0",
                "planets": "3",
                "ships_on_planets": "50",
                "ships_in_fleets": "10",
                "production": "3",
                "fleets": "1",
            }
        ],
    )

    analyze_run.main([str(run_dir), "--focus-agent", "candidate"])

    assert (run_dir / "leaderboard.csv").exists()
    assert (run_dir / "matchup_matrix.csv").exists()
    assert (run_dir / "phase_metrics.csv").exists()
    assert "candidate" in (run_dir / "leaderboard.md").read_text(encoding="utf-8")
    assert "Slot 1 ended with status ERROR" in (run_dir / "issue_report.md").read_text(encoding="utf-8")


def test_compare_runs_writes_delta_csv(tmp_path: Path):
    from tools.compare_runs import compare_run_dirs

    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write_csv(
        baseline / "leaderboard.csv",
        [{"agent": "candidate", "games": "10", "wins": "5", "win_rate": "0.5", "avg_reward": "0.0"}],
    )
    _write_csv(
        candidate / "leaderboard.csv",
        [{"agent": "candidate", "games": "12", "wins": "8", "win_rate": "0.6666666667", "avg_reward": "0.25"}],
    )

    out_path = compare_run_dirs(baseline, candidate, tmp_path / "delta.csv")

    rows = list(csv.DictReader(out_path.open(newline="", encoding="utf-8")))
    assert rows[0]["agent"] == "candidate"
    assert float(rows[0]["win_rate_delta"]) > 0.16

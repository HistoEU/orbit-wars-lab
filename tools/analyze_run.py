from __future__ import annotations

import argparse
import ast
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.orbitlab.analytics import build_leaderboard, build_matchup_matrix, summarize_phase_metrics
from src.orbitlab.detectors import detect_crashes, detect_slot_bias, detect_timeout_or_slow_match
from src.orbitlab.issues import Issue
from src.orbitlab.storage import write_csv


def _read_csv(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _decode_list(value):
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or value == "":
        return []
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def _decode_match_rows(matches: list[dict]) -> list[dict]:
    decoded = []
    for match in matches:
        row = dict(match)
        row["agents"] = _decode_list(row.get("agents"))
        row["rewards"] = _decode_list(row.get("rewards"))
        row["statuses"] = _decode_list(row.get("statuses"))
        try:
            row["elapsed_seconds"] = float(row.get("elapsed_seconds", 0))
        except ValueError:
            row["elapsed_seconds"] = 0.0
        try:
            row["steps"] = int(row.get("steps", 0))
        except ValueError:
            row["steps"] = 0
        if row.get("winner_agent") in ("", "None"):
            row["winner_agent"] = None
        decoded.append(row)
    return decoded


def _write_issues(path: Path, issues: list[Issue]) -> None:
    rows = [
        {
            "detector": issue.detector,
            "severity": issue.severity,
            "match_id": issue.match_id,
            "step": issue.step,
            "slot": issue.slot,
            "message": issue.message,
            "evidence": issue.evidence or {},
        }
        for issue in issues
    ]
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_report(path: Path, issues: list[Issue]) -> None:
    lines = ["# Orbit Wars Run Issue Report", ""]
    if not issues:
        lines.append("No issues detected.")
    for severity in ["P0", "P1", "P2", "P3"]:
        subset = [issue for issue in issues if issue.severity == severity]
        if not subset:
            continue
        lines.append(f"## {severity}")
        for issue in subset:
            where = f" match={issue.match_id}"
            if issue.step is not None:
                where += f" step={issue.step}"
            if issue.slot is not None:
                where += f" slot={issue.slot}"
            lines.append(f"- `{issue.detector}`{where}: {issue.message}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_leaderboard_report(path: Path, leaderboard: list[dict], matchup_matrix: list[dict]) -> None:
    lines = ["# Orbit Wars Leaderboard", ""]
    if not leaderboard:
        lines.append("No matches found.")
    else:
        lines.append("| Agent | Games | Wins | Win Rate | Avg Reward | Avg Steps |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for row in leaderboard:
            lines.append(
                f"| {row['agent']} | {row['games']} | {row['wins']} | "
                f"{row['win_rate']:.3f} | {row['avg_reward']:.3f} | {row['avg_steps']:.1f} |"
            )
    if matchup_matrix:
        lines.extend(["", "## Matchups", "", "| Matchup | Agent | Games | Wins | Losses | Draws | Win Rate |"])
        lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
        for row in matchup_matrix:
            lines.append(
                f"| {row['matchup']} | {row['agent']} | {row['games']} | {row['wins']} | "
                f"{row['losses']} | {row['draws']} | {row['win_rate']:.3f} |"
            )
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Analyze a tournament run directory for known flaw patterns.")
    parser.add_argument("run_dir")
    parser.add_argument("--focus-agent", default=None)
    parser.add_argument("--slow-threshold", type=float, default=30.0)
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    matches = _decode_match_rows(_read_csv(run_dir / "matches.csv"))
    turn_metrics = _read_csv(run_dir / "turn_metrics.csv")
    issues: list[Issue] = []
    for match in matches:
        issues.extend(detect_crashes(match))
        issues.extend(detect_timeout_or_slow_match(match, args.slow_threshold))
    if args.focus_agent:
        issues.extend(detect_slot_bias(matches, args.focus_agent, min_games_per_slot=20))

    leaderboard = build_leaderboard(matches)
    matchup_matrix = build_matchup_matrix(matches)
    phase_metrics = summarize_phase_metrics(turn_metrics, matches)
    write_csv(run_dir / "leaderboard.csv", leaderboard)
    write_csv(run_dir / "matchup_matrix.csv", matchup_matrix)
    write_csv(run_dir / "phase_metrics.csv", phase_metrics)
    _write_leaderboard_report(run_dir / "leaderboard.md", leaderboard, matchup_matrix)
    _write_issues(run_dir / "issues_analyzed.csv", issues)
    _write_report(run_dir / "issue_report.md", issues)
    print(run_dir / "issue_report.md")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.orbitlab.detectors import detect_crashes, detect_slot_bias, detect_timeout_or_slow_match
from src.orbitlab.issues import Issue


def _read_csv(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a tournament run directory for known flaw patterns.")
    parser.add_argument("run_dir")
    parser.add_argument("--focus-agent", default=None)
    parser.add_argument("--slow-threshold", type=float, default=30.0)
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    matches = _read_csv(run_dir / "matches.csv")
    issues: list[Issue] = []
    for match in matches:
        match["statuses"] = match.get("statuses", "").strip("[]").replace("'", "").split(", ") if isinstance(match.get("statuses"), str) else match.get("statuses", [])
        try:
            match["elapsed_seconds"] = float(match.get("elapsed_seconds", 0))
        except ValueError:
            match["elapsed_seconds"] = 0.0
        issues.extend(detect_crashes(match))
        issues.extend(detect_timeout_or_slow_match(match, args.slow_threshold))
    if args.focus_agent:
        issues.extend(detect_slot_bias(matches, args.focus_agent, min_games_per_slot=20))
    _write_issues(run_dir / "issues_analyzed.csv", issues)
    _write_report(run_dir / "issue_report.md", issues)
    print(run_dir / "issue_report.md")


if __name__ == "__main__":
    main()

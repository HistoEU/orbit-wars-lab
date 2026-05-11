from __future__ import annotations

import datetime as dt
import itertools
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .detectors import detect_match_issues
from .issues import Issue
from .reporting import write_summary
from .storage import init_db, insert_issue, insert_match, insert_run, insert_turn_metric, read_matches, write_csv
from .tournament import run_match


def _rotations(agents: list[str], player_count: int, rotate_slots: bool) -> list[list[str]]:
    if not rotate_slots:
        return [agents]
    if len(agents) != player_count:
        return [agents]
    if player_count == 2:
        return [agents, [agents[1], agents[0]]]
    return [agents[i:] + agents[:i] for i in range(player_count)]


def _scheduled_matches(config: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
    jobs = []
    seeds = [int(seed) for seed in config.get("seeds", [])]
    for matchup in config.get("matchups", []):
        name = matchup["name"]
        base_agents = list(matchup["agents"])
        player_count = int(matchup.get("player_count", len(base_agents)))
        for seed in seeds:
            for rotation_index, agents in enumerate(_rotations(base_agents, player_count, bool(matchup.get("rotate_slots", True)))):
                jobs.append(
                    {
                        "seed": seed,
                        "agents": agents,
                        "player_count": player_count,
                        "debug": bool(matchup.get("debug", True)),
                        "match_id": f"{name}__seed_{seed}__rot_{rotation_index}",
                        "matchup": name,
                        "run_id": run_id,
                    }
                )
    return jobs


def _run_job(job: dict[str, Any]) -> dict[str, Any]:
    return run_match(**job)


def _issue_to_row(issue: Issue, index: int) -> dict[str, Any]:
    return {
        "issue_id": f"{issue.match_id}__{issue.detector}__{index}",
        "match_id": issue.match_id,
        "detector": issue.detector,
        "severity": issue.severity,
        "step": issue.step,
        "slot": issue.slot,
        "message": issue.message,
        "evidence": issue.evidence or {},
    }


def run_tournament_from_config(config: dict[str, Any], out_dir: str | Path | None = None) -> str:
    created_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    label = str(config.get("label", "orbit_wars_run"))
    run_id = f"{stamp}_{label}"
    base_dir = Path(out_dir) if out_dir is not None else Path("runs")
    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    db_path = run_dir / "results.sqlite"
    init_db(db_path)
    insert_run(db_path, run_id, created_at, label, config)

    jobs = _scheduled_matches(config, run_id)
    workers = max(1, int(config.get("workers", 1)))
    if workers == 1:
        results = [_run_job(job) for job in jobs]
    else:
        results = []
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_job, job) for job in jobs]
            for future in as_completed(futures):
                results.append(future.result())
        results.sort(key=lambda row: row["match_id"])

    all_issues = []
    all_metrics = []
    for result in results:
        metrics = result.pop("turn_metrics", [])
        insert_match(db_path, result)
        for metric in metrics:
            insert_turn_metric(db_path, metric)
        all_metrics.extend(metrics)
        for index, issue in enumerate(detect_match_issues(result)):
            row = _issue_to_row(issue, index)
            insert_issue(db_path, row)
            all_issues.append(row)

    matches = read_matches(db_path)
    write_csv(run_dir / "matches.csv", matches)
    write_csv(run_dir / "turn_metrics.csv", all_metrics)
    write_csv(run_dir / "issues.csv", all_issues)
    write_summary(run_dir, matches)
    return str(run_dir)

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .storage import write_csv


def summarize_matches(matches: list[dict], focus_agent: str) -> dict:
    games = len(matches)
    wins = sum(1 for match in matches if match.get("winner_agent") == focus_agent)
    crashes = sum(1 for match in matches if any(status != "DONE" for status in match.get("statuses", [])))
    rewards = []
    for match in matches:
        agents = match.get("agents", [])
        if focus_agent in agents:
            slot = agents.index(focus_agent)
            reward = match.get("rewards", [0] * len(agents))[slot]
            if reward is not None:
                rewards.append(reward)
    return {
        "agent": focus_agent,
        "games": games,
        "wins": wins,
        "win_rate": wins / games if games else 0.0,
        "avg_reward": sum(rewards) / len(rewards) if rewards else 0.0,
        "crashes": crashes,
        "crash_rate": crashes / games if games else 0.0,
    }


def build_summary_rows(matches: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    agents = sorted({agent for match in matches for agent in match.get("agents", [])})
    for match in matches:
        for agent in agents:
            if agent in match.get("agents", []):
                grouped[(match.get("matchup", ""), agent)].append(match)
    rows = []
    for (matchup, agent), subset in sorted(grouped.items()):
        summary = summarize_matches(subset, agent)
        rows.append({"matchup": matchup, **summary})
    return rows


def write_summary(run_dir: str | Path, matches: list[dict]) -> list[dict]:
    rows = build_summary_rows(matches)
    write_csv(Path(run_dir) / "summary.csv", rows)
    return rows

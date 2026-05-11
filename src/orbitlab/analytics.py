from __future__ import annotations

import ast
import math
from collections import defaultdict
from typing import Any, Iterable


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None or value == "":
        return []
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _winner(match: dict[str, Any]) -> str | None:
    winner = match.get("winner_agent")
    return str(winner) if winner not in (None, "", "None") else None


def wilson_interval(wins: int, games: int, z: float = 1.96) -> tuple[float, float]:
    if games <= 0:
        return 0.0, 0.0
    p_hat = wins / games
    denominator = 1 + z * z / games
    center = (p_hat + z * z / (2 * games)) / denominator
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z * z / (4 * games)) / games) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def build_leaderboard(matches: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows_by_agent: dict[str, dict[str, Any]] = {}
    slot_counts: dict[str, defaultdict[int, int]] = defaultdict(lambda: defaultdict(int))
    slot_wins: dict[str, defaultdict[int, int]] = defaultdict(lambda: defaultdict(int))
    rewards: dict[str, list[float]] = defaultdict(list)
    steps: dict[str, list[int]] = defaultdict(list)

    for match in matches:
        agents = [str(agent) for agent in _as_list(match.get("agents"))]
        match_winner = _winner(match)
        match_rewards = _as_list(match.get("rewards"))
        for slot, agent in enumerate(agents):
            row = rows_by_agent.setdefault(
                agent,
                {"agent": agent, "games": 0, "wins": 0, "losses": 0, "draws": 0},
            )
            row["games"] += 1
            slot_counts[agent][slot] += 1
            if match_winner == agent:
                row["wins"] += 1
                slot_wins[agent][slot] += 1
            elif match_winner is None:
                row["draws"] += 1
            else:
                row["losses"] += 1
            if slot < len(match_rewards) and match_rewards[slot] not in (None, ""):
                rewards[agent].append(_as_float(match_rewards[slot]))
            steps[agent].append(_as_int(match.get("steps")))

    rows = []
    for agent, row in rows_by_agent.items():
        games = row["games"]
        wins = row["wins"]
        low, high = wilson_interval(wins, games)
        full_row = {
            **row,
            "win_rate": wins / games if games else 0.0,
            "win_rate_ci_low": low,
            "win_rate_ci_high": high,
            "avg_reward": sum(rewards[agent]) / len(rewards[agent]) if rewards[agent] else 0.0,
            "avg_steps": sum(steps[agent]) / len(steps[agent]) if steps[agent] else 0.0,
        }
        max_slot = max(slot_counts[agent].keys(), default=-1)
        for slot in range(max_slot + 1):
            slot_games = slot_counts[agent][slot]
            full_row[f"slot_{slot}_games"] = slot_games
            full_row[f"slot_{slot}_wins"] = slot_wins[agent][slot]
            full_row[f"slot_{slot}_win_rate"] = slot_wins[agent][slot] / slot_games if slot_games else 0.0
        rows.append(full_row)

    return sorted(rows, key=lambda item: (-item["win_rate"], -item["avg_reward"], -item["games"], item["agent"]))


def build_matchup_matrix(matches: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for match in matches:
        agents = [str(agent) for agent in _as_list(match.get("agents"))]
        matchup = str(match.get("matchup") or "unknown")
        match_winner = _winner(match)
        for agent in agents:
            key = (matchup, agent)
            row = grouped.setdefault(
                key,
                {
                    "matchup": matchup,
                    "agent": agent,
                    "games": 0,
                    "wins": 0,
                    "losses": 0,
                    "draws": 0,
                },
            )
            row["games"] += 1
            if match_winner == agent:
                row["wins"] += 1
            elif match_winner is None:
                row["draws"] += 1
            else:
                row["losses"] += 1

    rows = []
    for row in grouped.values():
        low, high = wilson_interval(row["wins"], row["games"])
        rows.append(
            {
                **row,
                "win_rate": row["wins"] / row["games"] if row["games"] else 0.0,
                "win_rate_ci_low": low,
                "win_rate_ci_high": high,
            }
        )
    return sorted(rows, key=lambda item: (item["matchup"], -item["win_rate"], item["agent"]))


def _phase_name(step: int, phase_edges: tuple[int, int]) -> str:
    if step < phase_edges[0]:
        return "early"
    if step < phase_edges[1]:
        return "mid"
    return "late"


def summarize_phase_metrics(
    metrics: Iterable[dict[str, Any]],
    matches: Iterable[dict[str, Any]],
    phase_edges: tuple[int, int] = (120, 300),
) -> list[dict[str, Any]]:
    match_agents = {str(match.get("match_id")): [str(agent) for agent in _as_list(match.get("agents"))] for match in matches}
    grouped: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for metric in metrics:
        match_id = str(metric.get("match_id"))
        agents = match_agents.get(match_id, [])
        slot = _as_int(metric.get("slot"), default=-1)
        if slot < 0 or slot >= len(agents):
            continue
        agent = agents[slot]
        phase = _phase_name(_as_int(metric.get("step")), phase_edges)
        key = (agent, phase)
        ships_on_planets = _as_float(metric.get("ships_on_planets"))
        ships_in_fleets = _as_float(metric.get("ships_in_fleets"))
        grouped[key]["samples"] += 1
        grouped[key]["planets"] += _as_float(metric.get("planets"))
        grouped[key]["ships_on_planets"] += ships_on_planets
        grouped[key]["ships_in_fleets"] += ships_in_fleets
        grouped[key]["total_ships"] += ships_on_planets + ships_in_fleets
        grouped[key]["production"] += _as_float(metric.get("production"))
        grouped[key]["fleets"] += _as_float(metric.get("fleets"))

    phase_rank = {"early": 0, "mid": 1, "late": 2}
    rows = []
    for (agent, phase), totals in grouped.items():
        samples = int(totals["samples"])
        rows.append(
            {
                "agent": agent,
                "phase": phase,
                "samples": samples,
                "avg_planets": totals["planets"] / samples,
                "avg_ships_on_planets": totals["ships_on_planets"] / samples,
                "avg_ships_in_fleets": totals["ships_in_fleets"] / samples,
                "avg_total_ships": totals["total_ships"] / samples,
                "avg_production": totals["production"] / samples,
                "avg_fleets": totals["fleets"] / samples,
            }
        )
    return sorted(rows, key=lambda item: (item["agent"], phase_rank[item["phase"]]))


def compare_agent_summaries(baseline_rows: Iterable[dict[str, Any]], candidate_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline_by_agent = {str(row.get("agent")): row for row in baseline_rows}
    candidate_by_agent = {str(row.get("agent")): row for row in candidate_rows}
    rows = []
    for agent in sorted(set(baseline_by_agent) & set(candidate_by_agent)):
        baseline = baseline_by_agent[agent]
        candidate = candidate_by_agent[agent]
        baseline_win_rate = _as_float(baseline.get("win_rate"))
        candidate_win_rate = _as_float(candidate.get("win_rate"))
        baseline_avg_reward = _as_float(baseline.get("avg_reward"))
        candidate_avg_reward = _as_float(candidate.get("avg_reward"))
        rows.append(
            {
                "agent": agent,
                "baseline_games": _as_int(baseline.get("games")),
                "candidate_games": _as_int(candidate.get("games")),
                "baseline_win_rate": baseline_win_rate,
                "candidate_win_rate": candidate_win_rate,
                "win_rate_delta": candidate_win_rate - baseline_win_rate,
                "baseline_avg_reward": baseline_avg_reward,
                "candidate_avg_reward": candidate_avg_reward,
                "avg_reward_delta": candidate_avg_reward - baseline_avg_reward,
            }
        )
    return rows

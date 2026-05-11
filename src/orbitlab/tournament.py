from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from kaggle_environments import make

from .adapters import read_field
from .replay import write_viewer_replay


def _winner_slot(rewards: list[int | float | None]) -> int | None:
    numeric = [reward if reward is not None else -10**9 for reward in rewards]
    if not numeric or max(numeric) == min(numeric):
        return None
    return int(numeric.index(max(numeric)))


def _turn_metrics(match_id: str, env: Any) -> list[dict[str, Any]]:
    metrics = []
    for step_index, step in enumerate(env.steps):
        for slot, state in enumerate(step):
            obs = getattr(state, "observation", None)
            if not obs:
                continue
            player = read_field(obs, "player", slot)
            planets = read_field(obs, "planets", []) or []
            fleets = read_field(obs, "fleets", []) or []
            owned_planets = [p for p in planets if int(p[1]) == int(player)]
            owned_fleets = [f for f in fleets if int(f[1]) == int(player)]
            metrics.append(
                {
                    "match_id": match_id,
                    "step": step_index,
                    "slot": slot,
                    "planets": len(owned_planets),
                    "ships_on_planets": sum(float(p[5]) for p in owned_planets),
                    "ships_in_fleets": sum(float(f[6]) for f in owned_fleets),
                    "production": sum(int(p[6]) for p in owned_planets),
                    "fleets": len(owned_fleets),
                }
            )
    return metrics


def run_match(
    seed: int,
    agents: list[str],
    player_count: int,
    debug: bool = True,
    match_id: str | None = None,
    matchup: str = "",
    run_id: str = "",
    viewer_replay_path: str | Path | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    match_id = match_id or f"{matchup or 'match'}__seed_{seed}__{'__'.join(str(i) for i in range(len(agents)))}"
    try:
        env = make("orbit_wars", configuration={"seed": int(seed)}, debug=debug)
        env.run(agents)
        final = env.steps[-1]
        rewards = [state.reward for state in final]
        statuses = [state.status for state in final]
        winner = _winner_slot(rewards)
        result = {
            "match_id": match_id,
            "run_id": run_id,
            "matchup": matchup,
            "seed": int(seed),
            "player_count": int(player_count),
            "agents": list(agents),
            "rewards": rewards,
            "statuses": statuses,
            "steps": len(env.steps),
            "winner_slot": winner,
            "elapsed_seconds": time.perf_counter() - start,
            "turn_metrics": _turn_metrics(match_id, env),
            "replay_path": None,
            "error_text": None,
        }
        if viewer_replay_path is not None:
            replay_path = write_viewer_replay(viewer_replay_path, result, env)
            result["replay_path"] = str(replay_path)
        return result
    except Exception as exc:
        return {
            "match_id": match_id,
            "run_id": run_id,
            "matchup": matchup,
            "seed": int(seed),
            "player_count": int(player_count),
            "agents": list(agents),
            "rewards": [None for _ in agents],
            "statuses": ["ERROR" for _ in agents],
            "steps": 0,
            "winner_slot": None,
            "elapsed_seconds": time.perf_counter() - start,
            "turn_metrics": [],
            "replay_path": None,
            "error_text": repr(exc),
        }

from __future__ import annotations

from typing import Any

from .adapters import parse_observation
from .mirror import step_once


def _obs_to_dict(obs: Any) -> dict[str, Any]:
    if isinstance(obs, dict):
        return obs
    keys = ["player", "planets", "fleets", "angular_velocity", "initial_planets", "comets", "comet_planet_ids", "remainingOverageTime"]
    return {key: getattr(obs, key) for key in keys if hasattr(obs, key)}


def extract_observation_frames(env: Any, player_slot: int = 0) -> list[dict[str, Any]]:
    frames = []
    for step_index, step in enumerate(getattr(env, "steps", []) or []):
        if player_slot >= len(step):
            continue
        obs = getattr(step[player_slot], "observation", None)
        if obs is None:
            continue
        frames.append({"step": step_index, "observation": _obs_to_dict(obs)})
    return frames


def _planet_errors(predicted, official) -> tuple[float, float, list[dict[str, Any]]]:
    official_by_id = {int(planet[0]): planet for planet in official}
    max_position_error = 0.0
    max_ship_error = 0.0
    mismatches = []
    for planet in predicted:
        official_planet = official_by_id.get(planet.id)
        if official_planet is None:
            mismatches.append({"type": "missing_planet", "planet_id": planet.id})
            continue
        position_error = max(abs(planet.x - float(official_planet[2])), abs(planet.y - float(official_planet[3])))
        ship_error = abs(float(planet.ships) - float(official_planet[5]))
        owner_error = int(planet.owner) != int(official_planet[1])
        max_position_error = max(max_position_error, position_error)
        max_ship_error = max(max_ship_error, ship_error)
        if position_error > 1e-9 or ship_error > 1e-9 or owner_error:
            mismatches.append(
                {
                    "type": "planet_mismatch",
                    "planet_id": planet.id,
                    "position_error": position_error,
                    "ship_error": ship_error,
                    "predicted_owner": planet.owner,
                    "official_owner": int(official_planet[1]),
                }
            )
    return max_position_error, max_ship_error, mismatches


def compare_mirror_to_official(frames: list[dict[str, Any]], max_steps: int = 5) -> dict[str, Any]:
    # The official environment's first visible transition keeps some orbiting
    # bodies at their initial positions, then subsequent transitions advance
    # from the current observation by one turn. Start at frame 1 until the
    # mirror state carries the official engine's internal step counter.
    start_index = 1 if len(frames) > 2 else 0
    checked_steps = min(max_steps, max(0, len(frames) - 1 - start_index))
    max_position_error = 0.0
    max_ship_error = 0.0
    mismatches = []
    for offset in range(checked_steps):
        index = start_index + offset
        state = parse_observation(frames[index]["observation"])
        predicted = step_once(state, {})
        official_next = frames[index + 1]["observation"].get("planets", [])
        position_error, ship_error, step_mismatches = _planet_errors(predicted.planets, official_next)
        max_position_error = max(max_position_error, position_error)
        max_ship_error = max(max_ship_error, ship_error)
        for mismatch in step_mismatches:
            mismatches.append({"step": frames[index]["step"], **mismatch})
    return {
        "checked_steps": checked_steps,
        "max_position_error": max_position_error,
        "max_ship_error": max_ship_error,
        "mismatches": mismatches,
        "unchecked_categories": [
            "combat_multi_fleet",
            "initial_rotation_transition",
            "submitted_agent_action_parity",
            "comet_spawn_transition",
            "moving_planet_sweep_collision",
        ],
    }

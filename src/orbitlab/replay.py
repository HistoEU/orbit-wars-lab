from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .adapters import read_field
from .physics import BOARD_SIZE, CENTER, SUN_RADIUS
from .replay_analysis import analyze_replay_payload, build_replay_analysis_summary


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted(_jsonable(item) for item in value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _state_observation(state: Any) -> Any:
    obs = read_field(state, "observation", None)
    return obs if obs is not None else {}


def _state_action(state: Any) -> Any:
    action = read_field(state, "action", [])
    return _jsonable(action or [])


def _frame_metrics(match_id: str, step: int, planets: list[list[Any]], fleets: list[list[Any]], player_count: int) -> list[dict[str, Any]]:
    rows = []
    for slot in range(player_count):
        owned_planets = [planet for planet in planets if int(planet[1]) == slot]
        owned_fleets = [fleet for fleet in fleets if int(fleet[1]) == slot]
        ships_on_planets = sum(float(planet[5]) for planet in owned_planets)
        ships_in_fleets = sum(float(fleet[6]) for fleet in owned_fleets)
        rows.append(
            {
                "match_id": match_id,
                "step": step,
                "slot": slot,
                "planets": len(owned_planets),
                "ships_on_planets": ships_on_planets,
                "ships_in_fleets": ships_in_fleets,
                "total_ships": ships_on_planets + ships_in_fleets,
                "production": sum(int(planet[6]) for planet in owned_planets),
                "fleets": len(owned_fleets),
            }
        )
    return rows


def _issue_row(issue: Any) -> dict[str, Any]:
    if isinstance(issue, dict):
        return _jsonable(issue)
    return {
        "detector": read_field(issue, "detector", ""),
        "severity": read_field(issue, "severity", ""),
        "message": read_field(issue, "message", ""),
        "match_id": read_field(issue, "match_id", ""),
        "step": read_field(issue, "step", None),
        "slot": read_field(issue, "slot", None),
        "evidence": _jsonable(read_field(issue, "evidence", {}) or {}),
    }


def _frame_derived(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not metrics:
        return {
            "leader_slot": None,
            "ship_spread": 0.0,
            "production_leader_slot": None,
            "planet_leader_slot": None,
            "pressure_leader_slot": None,
        }
    totals = [(int(row["slot"]), float(row.get("total_ships", 0.0))) for row in metrics]
    productions = [(int(row["slot"]), float(row.get("production", 0.0))) for row in metrics]
    planets = [(int(row["slot"]), float(row.get("planets", 0.0))) for row in metrics]
    pressure = [(int(row["slot"]), float(row.get("ships_in_fleets", 0.0))) for row in metrics]
    leader_slot, leader_ships = max(totals, key=lambda item: item[1])
    _, min_ships = min(totals, key=lambda item: item[1])
    return {
        "leader_slot": leader_slot,
        "ship_spread": leader_ships - min_ships,
        "production_leader_slot": max(productions, key=lambda item: item[1])[0],
        "planet_leader_slot": max(planets, key=lambda item: item[1])[0],
        "pressure_leader_slot": max(pressure, key=lambda item: item[1])[0],
    }


def build_viewer_replay(
    match: dict[str, Any],
    env: Any,
    issues: list[Any] | None = None,
    notes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    match_id = str(match.get("match_id", "manual"))
    player_count = int(match.get("player_count", len(match.get("agents", [])) or 2))
    frames = []
    for step_index, step_states in enumerate(getattr(env, "steps", []) or []):
        obs = {}
        for state in step_states:
            candidate = _state_observation(state)
            if read_field(candidate, "planets", None) is not None:
                obs = candidate
                break
        planets = _jsonable(read_field(obs, "planets", []) or [])
        fleets = _jsonable(read_field(obs, "fleets", []) or [])
        actions = [_state_action(state) for state in step_states]
        metrics = _frame_metrics(match_id, step_index, planets, fleets, player_count)
        frames.append(
            {
                "step": step_index,
                "planets": planets,
                "fleets": fleets,
                "comets": _jsonable(read_field(obs, "comets", []) or []),
                "comet_planet_ids": _jsonable(read_field(obs, "comet_planet_ids", []) or []),
                "metrics": metrics,
                "derived": _frame_derived(metrics),
                "actions": actions,
            }
        )

    payload = {
        "schema_version": 1,
        "game": "orbit_wars",
        "match_id": match_id,
        "run_id": str(match.get("run_id", "")),
        "matchup": str(match.get("matchup", "")),
        "seed": int(match.get("seed", 0)),
        "player_count": player_count,
        "agents": _jsonable(match.get("agents", [])),
        "rewards": _jsonable(match.get("rewards", [])),
        "statuses": _jsonable(match.get("statuses", [])),
        "winner_slot": match.get("winner_slot"),
        "board": {"size": BOARD_SIZE, "center": [CENTER, CENTER], "sun_radius": SUN_RADIUS},
        "frames": frames,
        "issues": [_issue_row(issue) for issue in (issues or [])],
        "notes": _jsonable(notes or []),
    }
    combined_issues = list(issues or []) + analyze_replay_payload(payload)
    payload["issues"] = [_issue_row(issue) for issue in combined_issues]
    payload["analysis"] = build_replay_analysis_summary(payload, combined_issues)
    return payload


def write_viewer_replay(
    path: str | Path,
    match: dict[str, Any],
    env: Any,
    issues: list[Any] | None = None,
    notes: list[dict[str, Any]] | None = None,
) -> Path:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    replay = build_viewer_replay(match, env, issues=issues, notes=notes)
    out_path.write_text(json.dumps(replay, indent=2), encoding="utf-8")
    return out_path


def merge_replay_issues(path: str | Path, issues: list[Any]) -> Path:
    replay_path = Path(path)
    payload = json.loads(replay_path.read_text(encoding="utf-8"))
    existing = payload.get("issues", [])
    payload["issues"] = existing + [_issue_row(issue) for issue in issues]
    payload["analysis"] = build_replay_analysis_summary(payload, [*_issues_from_rows(existing), *issues])
    replay_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return replay_path


def _issues_from_rows(rows: list[dict[str, Any]]) -> list[Any]:
    return rows

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from .collision import is_out_of_bounds, segment_hits_sun, segment_progress_to_circle
from .issues import Issue
from .physics import BOARD_SIZE, fleet_speed, launch_point


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


def _distance(a: list[Any], b: list[Any]) -> float:
    return math.hypot(_as_float(a[2]) - _as_float(b[2]), _as_float(a[3]) - _as_float(b[3]))


def _planets_by_id(frame: dict[str, Any]) -> dict[int, list[Any]]:
    return {_as_int(planet[0]): planet for planet in frame.get("planets", [])}


def _fleets_by_id(frame: dict[str, Any]) -> dict[int, list[Any]]:
    return {_as_int(fleet[0]): fleet for fleet in frame.get("fleets", [])}


def _metrics_by_slot(frame: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {_as_int(metric.get("slot")): metric for metric in frame.get("metrics", [])}


def _slot_actions(frame: dict[str, Any], slot: int) -> list[list[Any]]:
    actions = frame.get("actions", [])
    if slot >= len(actions) or not isinstance(actions[slot], list):
        return []
    return [action for action in actions[slot] if isinstance(action, list) and len(action) >= 3]


def _issue_key(issue: Issue) -> tuple[Any, ...]:
    evidence = issue.evidence or {}
    return (
        issue.detector,
        issue.severity,
        issue.match_id,
        issue.step,
        issue.slot,
        evidence.get("fleet_id"),
        evidence.get("planet_id"),
        evidence.get("comet_id"),
    )


def _dedupe(issues: list[Issue]) -> list[Issue]:
    seen = set()
    deduped = []
    for issue in issues:
        key = _issue_key(issue)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped


def detect_bad_launches(replay: dict[str, Any]) -> list[Issue]:
    match_id = str(replay.get("match_id", ""))
    issues = []
    for frame in replay.get("frames", []):
        planets_by_id = _planets_by_id(frame)
        step = _as_int(frame.get("step"))
        player_count = _as_int(replay.get("player_count"), default=len(frame.get("actions", [])))
        for slot in range(player_count):
            for action in _slot_actions(frame, slot):
                planet = planets_by_id.get(_as_int(action[0]))
                if not planet:
                    continue
                angle = _as_float(action[1])
                ships = _as_int(action[2])
                sx, sy = launch_point(_as_float(planet[2]), _as_float(planet[3]), _as_float(planet[4]), angle)
                far_x = sx + math.cos(angle) * BOARD_SIZE * 2
                far_y = sy + math.sin(angle) * BOARD_SIZE * 2
                sun_progress = segment_progress_to_circle(50.0, 50.0, 10.0, sx, sy, far_x, far_y)
                if sun_progress is None:
                    continue
                blocking_planet = None
                for other in frame.get("planets", []):
                    if _as_int(other[0]) == _as_int(planet[0]):
                        continue
                    planet_progress = segment_progress_to_circle(
                        _as_float(other[2]),
                        _as_float(other[3]),
                        _as_float(other[4]),
                        sx,
                        sy,
                        far_x,
                        far_y,
                    )
                    if planet_progress is not None and planet_progress < sun_progress:
                        blocking_planet = other
                        break
                if blocking_planet is None:
                    issues.append(
                        Issue(
                            detector="bad_launch_sun_lane",
                            severity="P1",
                            message="Launch ray crosses the sun danger radius before reaching the far side of the board.",
                            match_id=match_id,
                            step=step,
                            slot=slot,
                            evidence={
                                "planet_id": _as_int(planet[0]),
                                "angle": angle,
                                "ships": ships,
                                "source": [_as_float(planet[2]), _as_float(planet[3])],
                            },
                        )
                    )
    return issues


def detect_sun_deaths(replay: dict[str, Any]) -> list[Issue]:
    match_id = str(replay.get("match_id", ""))
    issues = []
    frames = replay.get("frames", [])
    for index in range(len(frames) - 1):
        frame = frames[index]
        next_frame = frames[index + 1]
        current_fleets = _fleets_by_id(frame)
        next_fleets = _fleets_by_id(next_frame)
        for fleet_id, fleet in current_fleets.items():
            if fleet_id in next_fleets:
                continue
            owner = _as_int(fleet[1])
            x = _as_float(fleet[2])
            y = _as_float(fleet[3])
            angle = _as_float(fleet[4])
            ships = _as_int(fleet[6])
            speed = fleet_speed(ships)
            end_x = x + math.cos(angle) * speed
            end_y = y + math.sin(angle) * speed
            if segment_hits_sun(x, y, end_x, end_y):
                issues.append(
                    Issue(
                        detector="sun_death",
                        severity="P1",
                        message="Fleet disappeared on a segment predicted to cross the sun danger radius.",
                        match_id=match_id,
                        step=_as_int(frame.get("step")),
                        slot=owner,
                        evidence={
                            "fleet_id": fleet_id,
                            "ships": ships,
                            "from": [x, y],
                            "predicted_to": [end_x, end_y],
                        },
                    )
                )
    return issues


def detect_missed_comets(replay: dict[str, Any]) -> list[Issue]:
    match_id = str(replay.get("match_id", ""))
    player_count = _as_int(replay.get("player_count"), default=2)
    issues = []
    seen: set[tuple[int, int]] = set()
    for frame in replay.get("frames", []):
        comet_ids = {_as_int(comet_id) for comet_id in frame.get("comet_planet_ids", [])}
        if not comet_ids:
            continue
        step = _as_int(frame.get("step"))
        planets = frame.get("planets", [])
        actions_by_slot = {slot: _slot_actions(frame, slot) for slot in range(player_count)}
        launched_planet_ids = {slot: {_as_int(action[0]) for action in actions} for slot, actions in actions_by_slot.items()}
        for comet in [planet for planet in planets if _as_int(planet[0]) in comet_ids and _as_int(planet[1]) < 0]:
            comet_id = _as_int(comet[0])
            comet_ships = _as_float(comet[5])
            for slot in range(player_count):
                key = (slot, comet_id)
                if key in seen:
                    continue
                owned_planets = [planet for planet in planets if _as_int(planet[1]) == slot and _as_int(planet[0]) not in launched_planet_ids[slot]]
                candidates = [
                    (planet, _distance(planet, comet))
                    for planet in owned_planets
                    if _as_float(planet[5]) >= comet_ships + 5 and _distance(planet, comet) <= 30.0
                ]
                if not candidates:
                    continue
                nearest, distance = min(candidates, key=lambda item: item[1])
                seen.add(key)
                issues.append(
                    Issue(
                        detector="missed_comet_window",
                        severity="P2",
                        message="Capturable neutral comet was close to an owned planet with enough ships, but no launch was made from that planet.",
                        match_id=match_id,
                        step=step,
                        slot=slot,
                        evidence={
                            "comet_id": comet_id,
                            "nearest_planet_id": _as_int(nearest[0]),
                            "distance": distance,
                            "available_ships": _as_float(nearest[5]),
                            "comet_ships": comet_ships,
                        },
                    )
                )
    return issues


def detect_replay_slow_expansion(replay: dict[str, Any], threshold_step: int = 60) -> list[Issue]:
    match_id = str(replay.get("match_id", ""))
    issues = []
    flagged_slots = set()
    for frame in replay.get("frames", []):
        step = _as_int(frame.get("step"))
        if step < threshold_step:
            continue
        for slot, metric in _metrics_by_slot(frame).items():
            if slot in flagged_slots:
                continue
            planets = _as_int(metric.get("planets"))
            if planets <= 1:
                flagged_slots.add(slot)
                issues.append(
                    Issue(
                        detector="slow_expansion",
                        severity="P2",
                        message="Bot still owned one or fewer planets after the early expansion threshold.",
                        match_id=match_id,
                        step=step,
                        slot=slot,
                        evidence={"planets": planets, "threshold_step": threshold_step},
                    )
                )
    return issues


def detect_idle_overstock(replay: dict[str, Any], min_idle_frames: int = 8) -> list[Issue]:
    match_id = str(replay.get("match_id", ""))
    streaks: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    issues = []
    flagged = set()
    for frame in replay.get("frames", []):
        step = _as_int(frame.get("step"))
        launched_planets = {
            _as_int(action[0])
            for slot in range(_as_int(replay.get("player_count"), default=2))
            for action in _slot_actions(frame, slot)
        }
        current_keys = set()
        for planet in frame.get("planets", []):
            owner = _as_int(planet[1])
            if owner < 0:
                continue
            key = (owner, _as_int(planet[0]))
            current_keys.add(key)
            if _as_float(planet[5]) >= 80.0 and _as_int(planet[6]) >= 4 and _as_int(planet[0]) not in launched_planets:
                streaks[key].append({"step": step, "planet": planet})
            else:
                streaks[key] = []
            if len(streaks[key]) >= min_idle_frames and key not in flagged:
                flagged.add(key)
                last = streaks[key][-1]["planet"]
                issues.append(
                    Issue(
                        detector="idle_overstock",
                        severity="P2",
                        message="High-production planet hoarded a large garrison without launching for several frames.",
                        match_id=match_id,
                        step=step,
                        slot=owner,
                        evidence={
                            "planet_id": _as_int(last[0]),
                            "ships": _as_float(last[5]),
                            "production": _as_int(last[6]),
                            "idle_frames": len(streaks[key]),
                        },
                    )
                )
        for key in list(streaks):
            if key not in current_keys:
                streaks[key] = []
    return issues


def detect_fleet_disappeared_without_capture(replay: dict[str, Any]) -> list[Issue]:
    match_id = str(replay.get("match_id", ""))
    issues = []
    frames = replay.get("frames", [])
    for index in range(len(frames) - 1):
        frame = frames[index]
        next_frame = frames[index + 1]
        current_fleets = _fleets_by_id(frame)
        next_fleets = _fleets_by_id(next_frame)
        current_planets = _planets_by_id(frame)
        next_planets = _planets_by_id(next_frame)
        for fleet_id, fleet in current_fleets.items():
            if fleet_id in next_fleets:
                continue
            owner = _as_int(fleet[1])
            x = _as_float(fleet[2])
            y = _as_float(fleet[3])
            angle = _as_float(fleet[4])
            ships = _as_int(fleet[6])
            speed = fleet_speed(ships)
            end_x = x + math.cos(angle) * speed
            end_y = y + math.sin(angle) * speed
            if segment_hits_sun(x, y, end_x, end_y) or is_out_of_bounds(end_x, end_y):
                continue
            captured = False
            for planet_id, next_planet in next_planets.items():
                previous_owner = _as_int(current_planets.get(planet_id, [None, None])[1], default=-99)
                if previous_owner != owner and _as_int(next_planet[1]) == owner:
                    captured = True
                    break
            if captured:
                continue
            issues.append(
                Issue(
                    detector="fleet_disappeared_without_capture",
                    severity="P2",
                    message="Fleet disappeared without a predicted sun/out-of-bounds cause and without capturing a planet.",
                    match_id=match_id,
                    step=_as_int(frame.get("step")),
                    slot=owner,
                    evidence={
                        "fleet_id": fleet_id,
                        "ships": ships,
                        "from": [x, y],
                        "predicted_to": [end_x, end_y],
                    },
                )
            )
    return issues


def detect_late_trailing_no_pressure(replay: dict[str, Any]) -> list[Issue]:
    match_id = str(replay.get("match_id", ""))
    issues = []
    flagged_slots = set()
    for frame in replay.get("frames", []):
        step = _as_int(frame.get("step"))
        if step < 350:
            continue
        metrics = _metrics_by_slot(frame)
        if not metrics:
            continue
        leader_total = max(_as_float(metric.get("total_ships")) for metric in metrics.values())
        for slot, metric in metrics.items():
            if slot in flagged_slots:
                continue
            total = _as_float(metric.get("total_ships"))
            ships_in_fleets = _as_float(metric.get("ships_in_fleets"))
            fleets = _as_int(metric.get("fleets"))
            deficit = leader_total - total
            if deficit >= 25.0 and fleets <= 1 and ships_in_fleets <= 5.0:
                flagged_slots.add(slot)
                issues.append(
                    Issue(
                        detector="late_trailing_no_pressure",
                        severity="P2",
                        message="Bot was trailing late but had little or no fleet pressure on the board.",
                        match_id=match_id,
                        step=step,
                        slot=slot,
                        evidence={
                            "ship_deficit": deficit,
                            "ships_in_fleets": ships_in_fleets,
                            "fleets": fleets,
                        },
                    )
                )
    return issues


def detect_overdefended_low_production(replay: dict[str, Any]) -> list[Issue]:
    match_id = str(replay.get("match_id", ""))
    issues = []
    flagged = set()
    for frame in replay.get("frames", []):
        metrics = _metrics_by_slot(frame)
        if not metrics:
            continue
        leader_planets = max(_as_int(metric.get("planets")) for metric in metrics.values())
        for planet in frame.get("planets", []):
            owner = _as_int(planet[1])
            if owner < 0:
                continue
            planet_id = _as_int(planet[0])
            key = (owner, planet_id)
            if key in flagged:
                continue
            owner_planets = _as_int(metrics.get(owner, {}).get("planets"))
            if _as_int(planet[6]) <= 2 and _as_float(planet[5]) >= 65.0 and owner_planets < leader_planets:
                flagged.add(key)
                issues.append(
                    Issue(
                        detector="overdefended_low_production",
                        severity="P3",
                        message="Low-production planet held a large garrison while the bot trailed in map control.",
                        match_id=match_id,
                        step=_as_int(frame.get("step")),
                        slot=owner,
                        evidence={
                            "planet_id": planet_id,
                            "ships": _as_float(planet[5]),
                            "production": _as_int(planet[6]),
                            "owner_planets": owner_planets,
                            "leader_planets": leader_planets,
                        },
                    )
                )
    return issues


def build_replay_analysis_summary(replay: dict[str, Any], issues: list[Issue]) -> dict[str, Any]:
    severity_counts = Counter(_issue_attr(issue, "severity") for issue in issues)
    detector_counts = Counter(_issue_attr(issue, "detector") for issue in issues)
    step_counts = Counter(str(_issue_attr(issue, "step")) for issue in issues if _issue_attr(issue, "step") is not None)
    return {
        "total_issues": len(issues),
        "severity_counts": dict(sorted(severity_counts.items())),
        "detector_counts": dict(sorted(detector_counts.items())),
        "issue_counts_by_step": dict(sorted(step_counts.items(), key=lambda item: int(item[0]))),
        "frame_count": len(replay.get("frames", [])),
    }


def _issue_attr(issue: Any, key: str) -> Any:
    if isinstance(issue, dict):
        return issue.get(key)
    return getattr(issue, key)


def analyze_replay_payload(replay: dict[str, Any]) -> list[Issue]:
    return _dedupe(
        detect_bad_launches(replay)
        + detect_sun_deaths(replay)
        + detect_missed_comets(replay)
        + detect_replay_slow_expansion(replay)
        + detect_idle_overstock(replay)
        + detect_fleet_disappeared_without_capture(replay)
        + detect_late_trailing_no_pressure(replay)
        + detect_overdefended_low_production(replay)
    )

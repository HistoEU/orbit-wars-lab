from __future__ import annotations

import math
from typing import Any

from .game_types import PlanetState

BOARD_SIZE = 100.0
CENTER = 50.0
SUN_RADIUS = 10.0
MAX_SPEED = 6.0
ROTATION_RADIUS_LIMIT = 50.0
LAUNCH_CLEARANCE = 0.1


def distance(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def orbital_radius(planet: PlanetState) -> float:
    return distance(planet.x, planet.y, CENTER, CENTER)


def is_orbiting(planet: PlanetState) -> bool:
    return orbital_radius(planet) + planet.radius < ROTATION_RADIUS_LIMIT


def fleet_speed(ships: int | float) -> float:
    ships = max(1.0, float(ships))
    ratio = math.log(ships) / math.log(1000.0)
    ratio = max(0.0, min(1.0, ratio))
    return 1.0 + (MAX_SPEED - 1.0) * (ratio**1.5)


def launch_point(sx: float, sy: float, radius: float, angle: float) -> tuple[float, float]:
    clearance = radius + LAUNCH_CLEARANCE
    return sx + math.cos(angle) * clearance, sy + math.sin(angle) * clearance


def predict_planet_position(
    planet: PlanetState,
    initial_by_id: dict[int, PlanetState],
    angular_velocity: float,
    turns: int | float,
) -> tuple[float, float]:
    initial = initial_by_id.get(planet.id, planet)
    if not is_orbiting(initial):
        return planet.x, planet.y
    radius = orbital_radius(initial)
    current_angle = math.atan2(planet.y - CENTER, planet.x - CENTER)
    future_angle = current_angle + angular_velocity * turns
    return CENTER + radius * math.cos(future_angle), CENTER + radius * math.sin(future_angle)


def predict_comet_position(planet_id: int, comets: tuple[dict[str, Any], ...] | list[dict[str, Any]], turns: int) -> tuple[float, float] | None:
    for group in comets:
        planet_ids = [int(x) for x in group.get("planet_ids", [])]
        if planet_id not in planet_ids:
            continue
        index = planet_ids.index(planet_id)
        paths = group.get("paths", [])
        path_index = int(group.get("path_index", 0)) + int(turns)
        if index >= len(paths):
            return None
        path = paths[index]
        if path_index < 0 or path_index >= len(path):
            return None
        return float(path[path_index][0]), float(path[path_index][1])
    return None


def advance_comet_groups(comets: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    advanced = []
    for group in comets:
        next_group = dict(group)
        next_group["path_index"] = int(group.get("path_index", 0)) + 1
        advanced.append(next_group)
    return tuple(advanced)


def comet_remaining_life(planet_id: int, comets: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> int:
    for group in comets:
        planet_ids = [int(x) for x in group.get("planet_ids", [])]
        if planet_id not in planet_ids:
            continue
        index = planet_ids.index(planet_id)
        paths = group.get("paths", [])
        path_index = int(group.get("path_index", 0))
        if index >= len(paths):
            return 0
        return max(0, len(paths[index]) - path_index)
    return 0


def estimate_arrival(
    sx: float,
    sy: float,
    sr: float,
    tx: float,
    ty: float,
    tr: float,
    ships: int,
) -> tuple[float, int] | None:
    from .collision import segment_hits_sun

    angle = math.atan2(ty - sy, tx - sx)
    start_x, start_y = launch_point(sx, sy, sr, angle)
    hit_distance = max(0.0, distance(sx, sy, tx, ty) - (sr + LAUNCH_CLEARANCE) - tr)
    end_x = start_x + math.cos(angle) * hit_distance
    end_y = start_y + math.sin(angle) * hit_distance
    if segment_hits_sun(start_x, start_y, end_x, end_y):
        return None
    turns = max(1, int(math.ceil(hit_distance / fleet_speed(ships))))
    return angle, turns

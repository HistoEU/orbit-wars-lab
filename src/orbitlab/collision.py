from __future__ import annotations

import math

from .game_types import PlanetState
from .physics import BOARD_SIZE, CENTER, SUN_RADIUS


def segment_circle_distance(
    cx: float,
    cy: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return math.hypot(cx - x1, cy - y1)
    t = ((cx - x1) * dx + (cy - y1) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    px = x1 + t * dx
    py = y1 + t * dy
    return math.hypot(cx - px, cy - py)


def segment_progress_to_circle(
    cx: float,
    cy: float,
    radius: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float | None:
    dx = x2 - x1
    dy = y2 - y1
    fx = x1 - cx
    fy = y1 - cy
    a = dx * dx + dy * dy
    b = 2.0 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - radius * radius
    if a <= 1e-12:
        return 0.0 if c <= 0 else None
    disc = b * b - 4.0 * a * c
    if disc < 0:
        return None
    root = math.sqrt(disc)
    candidates = [(-b - root) / (2.0 * a), (-b + root) / (2.0 * a)]
    valid = [t for t in candidates if 0.0 <= t <= 1.0]
    if not valid:
        return None
    return min(valid)


def segment_hits_circle(
    cx: float,
    cy: float,
    radius: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> bool:
    return segment_circle_distance(cx, cy, x1, y1, x2, y2) <= radius


def segment_hits_sun(x1: float, y1: float, x2: float, y2: float) -> bool:
    return segment_hits_circle(CENTER, CENTER, SUN_RADIUS, x1, y1, x2, y2)


def is_out_of_bounds(x: float, y: float) -> bool:
    return x < 0.0 or y < 0.0 or x > BOARD_SIZE or y > BOARD_SIZE


def first_planet_collision(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    planets: tuple[PlanetState, ...] | list[PlanetState],
) -> PlanetState | None:
    best: tuple[float, PlanetState] | None = None
    for planet in planets:
        progress = segment_progress_to_circle(planet.x, planet.y, planet.radius, x1, y1, x2, y2)
        if progress is None:
            continue
        if best is None or progress < best[0]:
            best = (progress, planet)
    return None if best is None else best[1]

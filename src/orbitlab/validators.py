from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .game_types import Move, PlanetState


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    planet_id: int | None = None


def validate_moves(player: int, planets: tuple[PlanetState, ...], moves: list[Move]) -> list[ValidationIssue]:
    planet_by_id = {planet.id: planet for planet in planets}
    launched: dict[int, int] = defaultdict(int)
    issues: list[ValidationIssue] = []

    for move in moves:
        planet = planet_by_id.get(move.from_planet_id)
        if planet is None:
            issues.append(ValidationIssue("unknown_source_planet", "Move references a missing planet.", move.from_planet_id))
            continue
        if planet.owner != player:
            issues.append(ValidationIssue("launch_from_unowned_planet", "Move launches from a planet not owned by this player.", planet.id))
            continue
        if move.ships <= 0:
            issues.append(ValidationIssue("nonpositive_launch", "Move launches zero or negative ships.", planet.id))
            continue
        launched[planet.id] += int(move.ships)
        if launched[planet.id] > int(planet.ships):
            issues.append(ValidationIssue("overlaunch", "Combined launches exceed available garrison.", planet.id))

    return issues

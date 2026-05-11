from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlanetState:
    id: int
    owner: int
    x: float
    y: float
    radius: float
    ships: float
    production: int


@dataclass(frozen=True)
class FleetState:
    id: int
    owner: int
    x: float
    y: float
    angle: float
    from_planet_id: int
    ships: int


@dataclass(frozen=True)
class Move:
    from_planet_id: int
    angle: float
    ships: int


@dataclass(frozen=True)
class ObservationState:
    player: int
    planets: tuple[PlanetState, ...]
    fleets: tuple[FleetState, ...]
    angular_velocity: float
    initial_planets: tuple[PlanetState, ...]
    comets: tuple[dict[str, Any], ...]
    comet_planet_ids: frozenset[int]
    remaining_overage_time: float | None


@dataclass(frozen=True)
class TurnMetric:
    match_id: str
    step: int
    slot: int
    planets: int
    ships_on_planets: float
    ships_in_fleets: float
    production: int
    fleets: int

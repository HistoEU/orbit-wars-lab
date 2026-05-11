from __future__ import annotations

from typing import Any

from .game_types import FleetState, Move, ObservationState, PlanetState


def read_field(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def parse_planet(raw: list[Any] | tuple[Any, ...] | PlanetState) -> PlanetState:
    if isinstance(raw, PlanetState):
        return raw
    return PlanetState(
        id=int(raw[0]),
        owner=int(raw[1]),
        x=float(raw[2]),
        y=float(raw[3]),
        radius=float(raw[4]),
        ships=float(raw[5]),
        production=int(raw[6]),
    )


def parse_fleet(raw: list[Any] | tuple[Any, ...] | FleetState) -> FleetState:
    if isinstance(raw, FleetState):
        return raw
    return FleetState(
        id=int(raw[0]),
        owner=int(raw[1]),
        x=float(raw[2]),
        y=float(raw[3]),
        angle=float(raw[4]),
        from_planet_id=int(raw[5]),
        ships=int(raw[6]),
    )


def parse_observation(obs: Any) -> ObservationState:
    return ObservationState(
        player=int(read_field(obs, "player", 0) or 0),
        planets=tuple(parse_planet(p) for p in (read_field(obs, "planets", []) or [])),
        fleets=tuple(parse_fleet(f) for f in (read_field(obs, "fleets", []) or [])),
        angular_velocity=float(read_field(obs, "angular_velocity", 0.0) or 0.0),
        initial_planets=tuple(parse_planet(p) for p in (read_field(obs, "initial_planets", []) or [])),
        comets=tuple(read_field(obs, "comets", []) or []),
        comet_planet_ids=frozenset(int(x) for x in (read_field(obs, "comet_planet_ids", []) or [])),
        remaining_overage_time=read_field(obs, "remainingOverageTime", None),
    )


def encode_move(move: Move) -> list[float | int]:
    return [int(move.from_planet_id), float(move.angle), int(move.ships)]

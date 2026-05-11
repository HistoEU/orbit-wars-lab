from __future__ import annotations

import math
from collections import defaultdict

from .collision import first_planet_collision, is_out_of_bounds, segment_hits_sun
from .combat import resolve_combat
from .game_types import FleetState, Move, ObservationState, PlanetState
from .physics import advance_comet_groups, fleet_speed, launch_point, predict_comet_position, predict_planet_position


def _remove_expired_comets(state: ObservationState) -> tuple[PlanetState, ...]:
    kept = []
    for planet in state.planets:
        if planet.id not in state.comet_planet_ids:
            kept.append(planet)
            continue
        if predict_comet_position(planet.id, state.comets, 0) is not None:
            kept.append(planet)
    return tuple(kept)


def _apply_launches(
    planets: tuple[PlanetState, ...],
    fleets: list[FleetState],
    actions_by_player: dict[int, list[Move]],
) -> tuple[tuple[PlanetState, ...], list[FleetState]]:
    next_planets = {planet.id: planet for planet in planets}
    next_fleet_id = 1 + max((fleet.id for fleet in fleets), default=0)

    for player, moves in actions_by_player.items():
        launched_by_planet: dict[int, int] = defaultdict(int)
        for move in moves:
            planet = next_planets.get(move.from_planet_id)
            if planet is None or planet.owner != player or move.ships <= 0:
                continue
            already = launched_by_planet[planet.id]
            send = min(int(move.ships), int(planet.ships) - already)
            if send <= 0:
                continue
            launched_by_planet[planet.id] += send
            sx, sy = launch_point(planet.x, planet.y, planet.radius, move.angle)
            fleets.append(FleetState(next_fleet_id, player, sx, sy, float(move.angle), planet.id, send))
            next_fleet_id += 1
        for planet_id, sent in launched_by_planet.items():
            planet = next_planets[planet_id]
            next_planets[planet_id] = PlanetState(
                planet.id, planet.owner, planet.x, planet.y, planet.radius, planet.ships - sent, planet.production
            )

    return tuple(sorted(next_planets.values(), key=lambda planet: planet.id)), fleets


def _produce(planets: tuple[PlanetState, ...]) -> tuple[PlanetState, ...]:
    produced = []
    for planet in planets:
        ships = planet.ships + planet.production if planet.owner != -1 else planet.ships
        produced.append(PlanetState(planet.id, planet.owner, planet.x, planet.y, planet.radius, ships, planet.production))
    return tuple(produced)


def _move_fleets(
    fleets: tuple[FleetState, ...] | list[FleetState],
    planets: tuple[PlanetState, ...],
) -> tuple[list[FleetState], dict[int, list[tuple[int, int]]]]:
    arrivals: dict[int, list[tuple[int, int]]] = defaultdict(list)
    survivors: list[FleetState] = []
    for fleet in fleets:
        speed = fleet_speed(fleet.ships)
        nx = fleet.x + math.cos(fleet.angle) * speed
        ny = fleet.y + math.sin(fleet.angle) * speed
        if segment_hits_sun(fleet.x, fleet.y, nx, ny) or is_out_of_bounds(nx, ny):
            continue
        hit = first_planet_collision(fleet.x, fleet.y, nx, ny, planets)
        if hit is not None:
            arrivals[hit.id].append((fleet.owner, fleet.ships))
            continue
        survivors.append(FleetState(fleet.id, fleet.owner, nx, ny, fleet.angle, fleet.from_planet_id, fleet.ships))
    return survivors, arrivals


def _advance_planets(state: ObservationState, planets: tuple[PlanetState, ...]) -> tuple[tuple[PlanetState, ...], tuple[dict, ...]]:
    initial_by_id = {planet.id: planet for planet in state.initial_planets}
    advanced_comets = advance_comet_groups(state.comets)
    advanced = []
    for planet in planets:
        if planet.id in state.comet_planet_ids:
            pos = predict_comet_position(planet.id, advanced_comets, 0)
            if pos is None:
                continue
            advanced.append(PlanetState(planet.id, planet.owner, pos[0], pos[1], planet.radius, planet.ships, planet.production))
            continue
        x, y = predict_planet_position(planet, initial_by_id, state.angular_velocity, 1)
        advanced.append(PlanetState(planet.id, planet.owner, x, y, planet.radius, planet.ships, planet.production))
    return tuple(sorted(advanced, key=lambda planet: planet.id)), advanced_comets


def _sweep_fleets(
    fleets: list[FleetState],
    planets: tuple[PlanetState, ...],
    arrivals: dict[int, list[tuple[int, int]]],
) -> list[FleetState]:
    survivors = []
    for fleet in fleets:
        hit = None
        for planet in planets:
            if math.hypot(fleet.x - planet.x, fleet.y - planet.y) <= planet.radius:
                hit = planet
                break
        if hit is None:
            survivors.append(fleet)
        else:
            arrivals[hit.id].append((fleet.owner, fleet.ships))
    return survivors


def _resolve_arrivals(planets: tuple[PlanetState, ...], arrivals: dict[int, list[tuple[int, int]]]) -> tuple[PlanetState, ...]:
    resolved = []
    for planet in planets:
        owner, ships = resolve_combat(planet.owner, planet.ships, arrivals.get(planet.id, []))
        resolved.append(PlanetState(planet.id, owner, planet.x, planet.y, planet.radius, ships, planet.production))
    return tuple(sorted(resolved, key=lambda planet: planet.id))


def step_once(state: ObservationState, actions_by_player: dict[int, list[Move]]) -> ObservationState:
    planets = _remove_expired_comets(state)
    planets, fleets = _apply_launches(planets, list(state.fleets), actions_by_player)
    planets = _produce(planets)
    fleets, arrivals = _move_fleets(fleets, planets)
    planets, comets = _advance_planets(state, planets)
    fleets = _sweep_fleets(fleets, planets, arrivals)
    planets = _resolve_arrivals(planets, arrivals)
    return ObservationState(
        player=state.player,
        planets=planets,
        fleets=tuple(sorted(fleets, key=lambda fleet: fleet.id)),
        angular_velocity=state.angular_velocity,
        initial_planets=state.initial_planets,
        comets=comets,
        comet_planet_ids=state.comet_planet_ids,
        remaining_overage_time=state.remaining_overage_time,
    )

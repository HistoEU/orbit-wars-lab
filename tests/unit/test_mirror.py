import math

from src.orbitlab.game_types import Move, ObservationState, PlanetState
from src.orbitlab.mirror import step_once


def make_state(planets, fleets=(), angular_velocity=0.0, comets=(), comet_ids=frozenset()):
    return ObservationState(
        player=0,
        planets=tuple(planets),
        fleets=tuple(fleets),
        angular_velocity=angular_velocity,
        initial_planets=tuple(planets),
        comets=tuple(comets),
        comet_planet_ids=frozenset(comet_ids),
        remaining_overage_time=None,
    )


def test_owned_planet_produces_after_launch():
    obs = make_state([
        PlanetState(1, 0, 10, 10, 2, 10, 3),
        PlanetState(2, -1, 30, 10, 2, 5, 1),
    ])
    next_state = step_once(obs, {0: [Move(1, 0.0, 4)]})
    source = next(p for p in next_state.planets if p.id == 1)
    assert source.ships == 9
    assert len(next_state.fleets) == 1


def test_fleet_collision_captures_planet():
    obs = make_state([
        PlanetState(1, 0, 10, 10, 2, 20, 3),
        PlanetState(2, -1, 15, 10, 2, 5, 1),
    ])
    next_state = step_once(obs, {0: [Move(1, 0.0, 8)]})
    target = next(p for p in next_state.planets if p.id == 2)
    assert target.owner == 0
    assert target.ships == 3


def test_fleet_that_crosses_sun_is_removed():
    obs = make_state([
        PlanetState(1, 0, 35, 50, 1, 1000, 3),
        PlanetState(2, -1, 80, 50, 2, 5, 1),
    ])
    next_state = step_once(obs, {0: [Move(1, 0.0, 1000)]})
    assert next_state.fleets == ()


def test_orbiting_planet_rotates_after_fleet_movement():
    planet = PlanetState(1, 0, 70, 50, 2, 10, 3)
    obs = make_state([planet], angular_velocity=math.pi / 2)
    next_state = step_once(obs, {})
    rotated = next_state.planets[0]
    assert round(rotated.x, 6) == 50.0
    assert round(rotated.y, 6) == 70.0


def test_comet_advances_along_path_and_expires():
    comet = PlanetState(99, 0, 1, 1, 1, 5, 1)
    comets = ({"planet_ids": [99], "paths": [[[1, 1], [2, 2]]], "path_index": 0},)
    obs = make_state([comet], comets=comets, comet_ids=frozenset({99}))
    next_state = step_once(obs, {})
    assert next_state.planets[0].x == 2.0
    assert next_state.planets[0].y == 2.0
    expired = step_once(next_state, {})
    assert expired.planets == ()

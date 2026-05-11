import math

from src.orbitlab.game_types import PlanetState
from src.orbitlab.physics import (
    CENTER,
    distance,
    estimate_arrival,
    fleet_speed,
    is_orbiting,
    launch_point,
    predict_comet_position,
    predict_planet_position,
)


def test_distance_uses_euclidean_metric():
    assert distance(0, 0, 3, 4) == 5


def test_fleet_speed_matches_official_formula():
    expected = 1.0 + 5.0 * ((math.log(100) / math.log(1000.0)) ** 1.5)
    assert fleet_speed(100) == expected
    assert fleet_speed(1) == 1.0
    assert fleet_speed(1000) == 6.0


def test_static_planet_does_not_rotate():
    planet = PlanetState(1, -1, 99.0, 50.0, 2.0, 10, 1)
    initial = {planet.id: planet}
    assert not is_orbiting(planet)
    assert predict_planet_position(planet, initial, 0.05, 20) == (99.0, 50.0)


def test_inner_planet_rotates_from_current_position():
    planet = PlanetState(1, -1, 70.0, 50.0, 2.0, 10, 1)
    initial = {planet.id: planet}
    x, y = predict_planet_position(planet, initial, math.pi / 2, 1)
    assert round(x, 6) == CENTER
    assert round(y, 6) == 70.0


def test_launch_point_starts_outside_source_radius():
    x, y = launch_point(10.0, 20.0, 3.0, 0.0)
    assert x == 13.1
    assert y == 20.0


def test_predict_comet_position_uses_path_index_plus_turns():
    comets = [{"planet_ids": [99], "paths": [[[1, 1], [2, 2], [3, 3]]], "path_index": 1}]
    assert predict_comet_position(99, comets, 1) == (3.0, 3.0)
    assert predict_comet_position(99, comets, 2) is None


def test_estimate_arrival_returns_angle_and_turns_for_safe_path():
    result = estimate_arrival(10.0, 10.0, 2.0, 20.0, 10.0, 2.0, 10)
    assert result is not None
    angle, turns = result
    assert angle == 0.0
    assert turns >= 1

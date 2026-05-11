from src.orbitlab.collision import (
    first_planet_collision,
    is_out_of_bounds,
    segment_circle_distance,
    segment_hits_circle,
    segment_hits_sun,
)
from src.orbitlab.game_types import PlanetState


def test_segment_circle_distance_for_crossing_segment():
    assert segment_circle_distance(50.0, 50.0, 0.0, 50.0, 100.0, 50.0) == 0.0


def test_segment_hits_sun_when_crossing_center():
    assert segment_hits_sun(0.0, 50.0, 100.0, 50.0)


def test_segment_does_not_hit_sun_when_clear():
    assert not segment_hits_sun(0.0, 0.0, 100.0, 0.0)


def test_out_of_bounds_detection():
    assert is_out_of_bounds(-0.1, 50.0)
    assert is_out_of_bounds(50.0, 100.1)
    assert not is_out_of_bounds(50.0, 50.0)


def test_segment_hits_planet_radius():
    assert segment_hits_circle(10.0, 10.0, 5.0, 0.0, 10.0, 20.0, 10.0)


def test_first_planet_collision_returns_earliest_planet():
    planets = (
        PlanetState(1, -1, 20.0, 10.0, 2.0, 5, 1),
        PlanetState(2, -1, 30.0, 10.0, 2.0, 5, 1),
    )
    hit = first_planet_collision(10.0, 10.0, 40.0, 10.0, planets)
    assert hit is not None
    assert hit.id == 1

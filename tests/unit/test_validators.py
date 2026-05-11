from src.orbitlab.game_types import Move, PlanetState
from src.orbitlab.validators import validate_moves


def test_rejects_launch_from_enemy_planet():
    planets = (PlanetState(1, 0, 10, 10, 2, 10, 1),)
    issues = validate_moves(player=1, planets=planets, moves=[Move(1, 0.0, 3)])
    assert issues[0].code == "launch_from_unowned_planet"


def test_rejects_overlaunch_across_multiple_moves():
    planets = (PlanetState(1, 0, 10, 10, 2, 10, 1),)
    issues = validate_moves(player=0, planets=planets, moves=[Move(1, 0.0, 7), Move(1, 1.0, 7)])
    assert issues[0].code == "overlaunch"


def test_accepts_multiple_legal_launches_from_same_planet():
    planets = (PlanetState(1, 0, 10, 10, 2, 10, 1),)
    issues = validate_moves(player=0, planets=planets, moves=[Move(1, 0.0, 4), Move(1, 1.0, 5)])
    assert issues == []

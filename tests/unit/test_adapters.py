from src.orbitlab.adapters import encode_move, parse_observation
from src.orbitlab.game_types import Move


def test_parse_observation_from_dict():
    obs = {
        "player": 2,
        "planets": [[1, 2, 10.0, 20.0, 2.0, 15, 3]],
        "fleets": [[5, 2, 11.0, 22.0, 0.5, 1, 7]],
        "angular_velocity": 0.035,
        "initial_planets": [[1, 2, 10.0, 20.0, 2.0, 15, 3]],
        "comets": [{"planet_ids": [99], "paths": [[[1.0, 2.0]]], "path_index": 0}],
        "comet_planet_ids": [99],
    }

    parsed = parse_observation(obs)

    assert parsed.player == 2
    assert parsed.planets[0].production == 3
    assert parsed.fleets[0].ships == 7
    assert 99 in parsed.comet_planet_ids


def test_encode_move_returns_kaggle_action_shape():
    assert encode_move(Move(3, 1.25, 8)) == [3, 1.25, 8]

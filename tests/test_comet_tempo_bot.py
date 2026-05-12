import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOT_PATH = ROOT / "bots" / "comet_tempo" / "main.py"


def load_bot():
    spec = importlib.util.spec_from_file_location("comet_tempo_bot", BOT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_comets_maps_id_to_remaining_life():
    bot = load_bot()
    obs = {
        "comets": [
            {"planet_ids": [9], "paths": [[[10, 10], [12, 10], [14, 10]]], "path_index": 1}
        ]
    }

    meta = bot.parse_comets(obs)

    assert meta[9]["remaining_life"] == 2
    assert meta[9]["path_index"] == 1


def test_comet_future_position_advances_along_path():
    bot = load_bot()
    meta = {
        9: {
            "path": [[10, 10], [12, 10], [14, 10], [16, 10]],
            "path_index": 1,
            "remaining_life": 3,
        }
    }

    assert bot.comet_future_position(9, meta, 2) == (16.0, 10.0)


def test_long_life_comet_scores_above_short_life_comet():
    bot = load_bot()
    source = bot.PlanetView(1, 0, 10, 10, 3, 90, 5)
    long_comet = bot.PlanetView(9, -1, 24, 10, 2, 8, 4, is_comet=True)
    short_comet = bot.PlanetView(10, -1, 24, 12, 2, 8, 4, is_comet=True)
    state = {"player": 0, "step": 80, "enemies": [], "mine": [source]}
    meta = {
        9: {"path": [[24, 10]] * 40, "path_index": 0, "remaining_life": 40},
        10: {"path": [[24, 12]] * 6, "path_index": 0, "remaining_life": 6},
    }

    long_score = bot.score_comet_candidate(source, long_comet, state, meta)
    short_score = bot.score_comet_candidate(source, short_comet, state, meta)

    assert long_score["score"] > short_score["score"]
    assert short_score["reason"] == "expires_too_soon"


def test_plan_comet_launches_takes_good_nearby_comet():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 80,
        "planets": [
            [1, 0, 10, 10, 3, 90, 5],
            [9, -1, 24, 10, 2, 8, 4],
        ],
        "fleets": [],
        "comet_planet_ids": [9],
        "comets": [{"planet_ids": [9], "paths": [[[24, 10]] * 40], "path_index": 0}],
    }
    state = bot.parse_state(obs)

    moves = bot.plan_comet_launches(state)

    assert moves
    assert moves[0][0] == 1
    assert moves[0][2] > 8


def test_plan_comet_launches_respects_source_reserve():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 80,
        "planets": [
            [1, 0, 10, 10, 3, 12, 5],
            [9, -1, 24, 10, 2, 8, 4],
        ],
        "fleets": [],
        "comet_planet_ids": [9],
        "comets": [{"planet_ids": [9], "paths": [[[24, 10]] * 40], "path_index": 0}],
    }
    state = bot.parse_state(obs)

    assert bot.plan_comet_launches(state) == []

import importlib.util
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOT_PATH = ROOT / "bots" / "pressure_raider" / "main.py"


def load_bot():
    spec = importlib.util.spec_from_file_location("pressure_raider_bot", BOT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_high_production_low_garrison_scores_high():
    bot = load_bot()
    source = bot.PlanetView(1, 0, 20, 20, 3, 100, 5)
    target = bot.PlanetView(8, 1, 35, 20, 3, 12, 6)
    state = {"step": 160, "player": 0, "player_count": 2, "mine": [source], "enemies": [target], "fleets": []}

    score = bot.pressure_score(source, target, state)

    assert score["score"] > 0
    assert score["purpose"] == "capture"


def test_low_production_high_garrison_scores_low():
    bot = load_bot()
    source = bot.PlanetView(1, 0, 20, 20, 3, 100, 5)
    target = bot.PlanetView(8, 1, 35, 20, 3, 80, 1)
    state = {"step": 160, "player": 0, "player_count": 2, "mine": [source], "enemies": [target], "fleets": []}

    score = bot.pressure_score(source, target, state)

    assert score["score"] < 0


def test_incoming_enemy_pressure_blocks_attack_spend():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 160,
        "planets": [
            [1, 0, 20, 20, 3, 45, 5],
            [8, 1, 35, 20, 3, 12, 6],
        ],
        "fleets": [[7, 1, 30, 20, math.pi, 8, 35]],
    }
    state = bot.parse_state(obs)

    assert bot.plan_pressure(state) == []


def test_late_behind_pressure_budget_is_larger():
    bot = load_bot()

    assert bot.pressure_budget_fraction({"step": 380, "ship_delta": -60}) > bot.pressure_budget_fraction({"step": 380, "ship_delta": 60})


def test_plan_pressure_launches_at_weak_enemy_planet():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 180,
        "planets": [
            [1, 0, 20, 20, 3, 120, 5],
            [8, 1, 35, 20, 3, 12, 6],
        ],
        "fleets": [],
    }
    state = bot.parse_state(obs)

    moves = bot.plan_pressure(state)

    assert moves
    assert moves[0][0] == 1
    assert moves[0][2] >= 14


def test_opening_first_capture_sends_enough_for_cheap_neutral():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 1,
        "planets": [
            [1, 0, 10, 10, 3, 10, 5],
            [2, -1, 24, 10, 2, 8, 4],
            [3, 1, 80, 80, 3, 60, 5],
        ],
        "fleets": [],
    }

    moves = bot.agent(obs)

    assert moves[0] == [1, 0.0, 9]


def test_expansion_fallback_does_not_trickle_underpowered_fleet():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 20,
        "planets": [
            [1, 0, 10, 10, 3, 10, 5],
            [2, -1, 24, 10, 2, 16, 4],
            [3, 1, 80, 80, 3, 60, 5],
        ],
        "fleets": [],
    }

    moves = bot.agent(obs)

    assert moves == []


def test_midgame_unthreatened_reserve_leaves_surplus_active():
    bot = load_bot()
    source = bot.PlanetView(1, 0, 20, 20, 3, 50, 5)
    state = {"step": 160, "player": 0, "mine": [source], "fleets": [], "incoming_by_planet": {1: 0}}

    reserve = bot.compute_reserve(source, state)

    assert reserve <= 8


def test_expansion_fallback_can_convert_weak_enemy_after_opening():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 140,
        "planets": [
            [1, 0, 10, 10, 3, 200, 5],
            [2, -1, 24, 10, 2, 8, 1],
            [3, 1, 10, 24, 2, 6, 6],
        ],
        "fleets": [],
    }
    state = bot.parse_state(obs)

    moves = bot.plan_expansion_fallback(state)

    assert moves[0][1] == math.pi / 2

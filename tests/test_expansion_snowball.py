import importlib.util
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOT_PATH = ROOT / "bots" / "expansion_snowball" / "main.py"


def load_bot():
    spec = importlib.util.spec_from_file_location("expansion_snowball_bot", BOT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_state_groups_planets_by_owner():
    bot = load_bot()
    obs = {
        "player": 0,
        "players": [0, 1],
        "step": 12,
        "planets": [
            [1, 0, 20, 20, 3, 50, 5],
            [2, 1, 80, 80, 3, 30, 4],
            [3, -1, 45, 20, 2, 10, 2],
        ],
        "fleets": [],
    }

    state = bot.parse_state(obs)

    assert len(state["mine"]) == 1
    assert len(state["enemies"]) == 1
    assert len(state["neutral"]) == 1
    assert state["player_count"] == 2


def test_score_prefers_high_production_safe_target_over_weak_target():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 20,
        "planets": [
            [1, 0, 12, 12, 3, 90, 5],
            [2, -1, 20, 12, 2, 8, 1],
            [3, -1, 28, 12, 2, 18, 5],
        ],
        "fleets": [],
    }
    state = bot.parse_state(obs)
    source = state["mine"][0]
    weak = next(p for p in state["neutral"] if p.id == 2)
    strong = next(p for p in state["neutral"] if p.id == 3)

    weak_score = bot.score_target(source, weak, state)
    strong_score = bot.score_target(source, strong, state)

    assert strong_score.score > weak_score.score
    assert strong_score.ships_required > weak_score.ships_required


def test_score_rejects_sun_blocked_direct_route():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 20,
        "planets": [
            [1, 0, 20, 50, 3, 100, 5],
            [2, -1, 80, 50, 3, 8, 5],
        ],
        "fleets": [],
    }
    state = bot.parse_state(obs)
    source = state["mine"][0]
    target = state["neutral"][0]

    scored = bot.score_target(source, target, state)

    assert scored.score < -9000
    assert scored.reason == "sun_blocked"


def test_incoming_enemy_fleet_raises_source_reserve():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 80,
        "planets": [[1, 0, 20, 50, 3, 100, 5]],
        "fleets": [[7, 1, 40, 50, math.pi, 9, 30]],
    }
    state = bot.parse_state(obs)
    source = state["mine"][0]

    reserve = bot.compute_reserve(source, state)

    assert reserve >= 37


def test_plan_moves_does_not_oversend_two_sources_to_one_target():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 90,
        "planets": [
            [1, 0, 10, 10, 3, 80, 5],
            [2, 0, 12, 14, 3, 80, 4],
            [3, -1, 24, 12, 2, 10, 4],
        ],
        "fleets": [],
    }
    state = bot.parse_state(obs)

    moves = bot.plan_moves(state)
    sent_to_target = sum(move[2] for move in moves)

    assert len(moves) >= 1
    assert sent_to_target <= 16


def test_agent_returns_legal_move_shape():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 5,
        "planets": [
            [1, 0, 10, 10, 3, 80, 5],
            [2, -1, 24, 10, 2, 8, 4],
        ],
        "fleets": [],
    }

    moves = bot.agent(obs)

    assert moves
    assert all(len(move) == 3 for move in moves)
    assert all(move[0] == 1 for move in moves)
    assert all(isinstance(move[1], float) for move in moves)
    assert all(isinstance(move[2], int) and move[2] > 0 for move in moves)

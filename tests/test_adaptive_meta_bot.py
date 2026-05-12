import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOT_PATH = ROOT / "bots" / "adaptive_meta" / "main.py"


def load_bot():
    spec = importlib.util.spec_from_file_location("adaptive_meta_bot", BOT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_compute_signals_detects_4p_midgame():
    bot = load_bot()
    obs = {
        "player": 0,
        "players": [0, 1, 2, 3],
        "step": 180,
        "planets": [
            [1, 0, 10, 10, 3, 80, 5],
            [2, 1, 80, 10, 3, 70, 4],
            [3, 2, 80, 80, 3, 70, 4],
            [4, 3, 10, 80, 3, 70, 4],
        ],
        "fleets": [],
    }

    signals = bot.compute_signals(bot.compute_game_state(obs))

    assert signals["phase"] == "mid"
    assert signals["player_count"] == 4


def test_mode_budget_changes_when_late_and_behind():
    bot = load_bot()

    late_behind = bot.choose_mode_budget({"phase": "late", "ship_delta": -80, "player_count": 2, "incoming_threat": 0})
    late_ahead = bot.choose_mode_budget({"phase": "late", "ship_delta": 80, "player_count": 2, "incoming_threat": 0})

    assert late_behind["PRESSURE"] > late_ahead["PRESSURE"]
    assert late_ahead["DEFEND"] > late_behind["DEFEND"]


def test_merge_proposals_blocks_source_double_spend():
    bot = load_bot()
    source = bot.PlanetView(1, 0, 10, 10, 3, 50, 5)
    ledger = bot.build_source_ledger([source], {1: 10})
    proposals = [
        {"planner": "EXPAND", "source_id": 1, "target_id": 2, "angle": 0.0, "ships": 30, "score": 50, "risk": 0},
        {"planner": "PRESSURE", "source_id": 1, "target_id": 3, "angle": 0.2, "ships": 30, "score": 45, "risk": 0},
    ]

    moves = bot.merge_proposals(proposals, ledger, {"EXPAND": 100, "PRESSURE": 100})

    assert len(moves) == 1
    assert moves[0][2] == 30


def test_agent_returns_legal_move_shape():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 30,
        "planets": [
            [1, 0, 10, 10, 3, 90, 5],
            [2, -1, 24, 10, 2, 8, 4],
            [3, 1, 80, 80, 3, 80, 5],
        ],
        "fleets": [],
    }

    moves = bot.agent(obs)

    assert moves
    assert all(len(move) == 3 for move in moves)
    assert all(isinstance(move[1], float) for move in moves)
    assert all(isinstance(move[2], int) and move[2] > 0 for move in moves)

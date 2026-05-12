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


def test_opening_first_capture_sends_enough_for_cheap_neutral():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 1,
        "planets": [
            [1, 0, 10, 10, 3, 10, 5],
            [2, -1, 24, 10, 2, 8, 4],
        ],
        "fleets": [],
    }

    moves = bot.agent(obs)

    assert moves == [[1, 0.0, 9]]


def test_stuck_single_planet_keeps_trying_full_cheap_capture_through_step_60():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 45,
        "planets": [
            [1, 0, 10, 10, 3, 12, 5],
            [2, -1, 24, 10, 2, 8, 4],
        ],
        "fleets": [],
    }

    moves = bot.agent(obs)

    assert moves == [[1, 0.0, 9]]


def test_midgame_safe_neutrals_are_not_starved_by_pressure_budget():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 140,
        "planets": [
            [1, 0, 10, 10, 3, 50, 5],
            [2, 0, 10, 30, 3, 50, 5],
            [3, -1, 22, 10, 2, 20, 4],
            [4, -1, 22, 30, 2, 20, 4],
        ],
        "fleets": [],
    }

    moves = bot.agent(obs)

    assert len(moves) >= 2
    assert sum(move[2] for move in moves) >= 52


def test_pressure_champion_path_can_punish_exposed_enemy_before_expansion():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 80,
        "planets": [
            [1, 0, 10, 10, 3, 500, 5],
            [2, -1, 24, 10, 2, 8, 5],
            [3, 1, 10, 24, 2, 10, 5],
        ],
        "fleets": [],
    }

    moves = bot.agent(obs)

    assert moves[0][1] == 3.141592653589793 / 2


def test_midgame_expansion_generator_can_target_weak_enemy_production():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 140,
        "planets": [
            [1, 0, 10, 10, 3, 120, 5],
            [2, -1, 24, 10, 2, 8, 2],
            [3, 1, 10, 24, 2, 6, 6],
        ],
        "fleets": [],
    }
    state = bot.compute_game_state(obs)
    signals = bot.compute_signals(state)

    proposals = bot.plan_expansion(state, signals)

    assert any(proposal["target_id"] == 3 for proposal in proposals)


def test_economy_plan_moves_available_for_champion_guard():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 140,
        "planets": [
            [1, 0, 10, 10, 3, 500, 5],
            [2, -1, 24, 10, 2, 8, 5],
            [3, 1, 10, 24, 2, 10, 5],
        ],
        "fleets": [],
    }
    state = bot.compute_game_state(obs)

    moves = bot.economy_plan_moves(state)

    assert moves[0] == [1, 0.0, 16]


def test_late_mode_controller_can_pressure_instead_of_static_economy_guard():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 320,
        "planets": [
            [1, 0, 10, 10, 3, 500, 5],
            [2, -1, 24, 10, 2, 8, 5],
            [3, 1, 10, 24, 2, 10, 5],
        ],
        "fleets": [],
    }

    moves = bot.agent(obs)

    assert moves[0][1] == 3.141592653589793 / 2


def test_late_behind_pressure_overrides_economy_guard():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 320,
        "planets": [
            [1, 0, 10, 10, 3, 120, 5],
            [2, -1, 24, 10, 2, 8, 4],
            [3, 1, 10, 24, 2, 6, 6],
            [4, 1, 80, 80, 3, 220, 5],
        ],
        "fleets": [],
    }

    moves = bot.agent(obs)

    assert moves[0][1] == 3.141592653589793 / 2

import importlib.util
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOT_PATH = ROOT / "bots" / "safe_geometry" / "main.py"


def load_bot():
    spec = importlib.util.spec_from_file_location("safe_geometry_bot", BOT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_angle_to_right_is_zero():
    bot = load_bot()

    assert abs(bot.angle_to(0, 0, 10, 0)) < 1e-9


def test_sun_collision_progress_happens_before_target():
    bot = load_bot()
    source = bot.PlanetView(1, 0, 20, 50, 3, 80, 5)
    target = bot.PlanetView(2, -1, 80, 50, 3, 8, 4)

    route = bot.plan_route(source, target, 12, allow_offsets=False)

    assert route is None


def test_direct_safe_target_returns_route_plan():
    bot = load_bot()
    source = bot.PlanetView(1, 0, 10, 10, 3, 80, 5)
    target = bot.PlanetView(2, -1, 30, 10, 2, 8, 4)

    route = bot.plan_route(source, target, 12)

    assert route is not None
    assert route["reason"] == "direct_safe"
    assert route["travel_turns"] > 0


def test_offset_route_can_rescue_sun_blocked_direct_route():
    bot = load_bot()
    source = bot.PlanetView(1, 0, 20, 35, 3, 80, 5)
    target = bot.PlanetView(2, -1, 80, 45, 8, 8, 4)

    direct = bot.plan_route(source, target, 12, allow_offsets=False)
    offset = bot.plan_route(source, target, 12, allow_offsets=True)

    assert direct is None
    assert offset is not None
    assert offset["reason"] == "offset_safe"


def test_orbit_prediction_changes_target_position():
    bot = load_bot()
    initial = bot.PlanetView(2, -1, 70, 50, 3, 8, 4)
    current = bot.PlanetView(2, -1, 70, 50, 3, 8, 4)

    x, y = bot.predict_orbiting_position(current, {2: initial}, angular_velocity=0.1, turns=10)

    assert not math.isclose(x, current.x)
    assert not math.isclose(y, current.y)


def test_agent_avoids_obvious_sun_death_launch():
    bot = load_bot()
    obs = {
        "player": 0,
        "step": 5,
        "planets": [
            [1, 0, 20, 50, 3, 80, 5],
            [2, -1, 80, 50, 3, 8, 4],
        ],
        "fleets": [],
    }

    moves = bot.agent(obs)

    assert moves == []

from src.orbitlab.tournament import run_match


def test_run_match_returns_rewards_and_statuses():
    result = run_match(
        seed=42,
        agents=["bots/starter/main.py", "bots/random_hold/main.py"],
        player_count=2,
        debug=True,
    )
    assert result["seed"] == 42
    assert result["rewards"] == [1, -1]
    assert result["statuses"] == ["DONE", "DONE"]
    assert result["steps"] > 0

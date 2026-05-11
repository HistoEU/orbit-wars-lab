from kaggle_environments import make

from src.orbitlab.parity import compare_mirror_to_official, extract_observation_frames


def test_mirror_matches_official_no_action_first_steps():
    env = make("orbit_wars", configuration={"seed": 42}, debug=True)
    env.run(["bots/random_hold/main.py", "bots/random_hold/main.py"])

    frames = extract_observation_frames(env, player_slot=0)
    report = compare_mirror_to_official(frames, max_steps=5)

    assert report["checked_steps"] == 5
    assert report["max_position_error"] <= 1e-9
    assert report["max_ship_error"] <= 1e-9
    assert report["mismatches"] == []
    assert "combat_multi_fleet" in report["unchecked_categories"]

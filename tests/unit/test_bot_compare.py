from src.orbitlab.bot_compare import build_compare_config


def test_build_compare_config_rotates_slots_and_can_export_replays():
    config = build_compare_config(
        candidate="bots/our_v1/main.py",
        baseline="bots/starter/main.py",
        seeds=[1, 2],
        workers=2,
        export_viewer_replays=True,
    )

    assert config["seeds"] == [1, 2]
    assert config["workers"] == 2
    assert config["export_viewer_replays"] is True
    assert config["matchups"][0]["name"] == "candidate_vs_baseline"
    assert config["matchups"][0]["agents"] == ["bots/our_v1/main.py", "bots/starter/main.py"]
    assert config["matchups"][0]["rotate_slots"] is True

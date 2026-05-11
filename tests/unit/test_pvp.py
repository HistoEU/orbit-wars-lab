from src.orbitlab.pvp import build_pvp_config


def test_build_2p_pvp_config_rotates_slots():
    config = build_pvp_config(
        agents=["bots/our_v1/main.py", "bots/starter/main.py"],
        seeds=[1, 2],
        workers=2,
        export_viewer_replays=True,
    )

    assert config["label"] == "pvp_2p"
    assert config["seeds"] == [1, 2]
    assert config["workers"] == 2
    assert config["export_viewer_replays"] is True
    assert config["matchups"][0]["name"] == "pvp_2p"
    assert config["matchups"][0]["player_count"] == 2
    assert config["matchups"][0]["rotate_slots"] is True


def test_build_4p_pvp_config_requires_four_agents():
    config = build_pvp_config(
        agents=["a.py", "b.py", "c.py", "d.py"],
        seeds=[7],
        player_count=4,
    )

    assert config["label"] == "pvp_4p"
    assert config["matchups"][0]["player_count"] == 4
    assert config["matchups"][0]["agents"] == ["a.py", "b.py", "c.py", "d.py"]

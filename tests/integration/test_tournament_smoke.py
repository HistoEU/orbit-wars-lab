from pathlib import Path

from kaggle_environments import make

from src.orbitlab.scheduler import run_tournament_from_config


def test_official_starter_beats_hold_bot_on_seed_42():
    env = make("orbit_wars", configuration={"seed": 42}, debug=True)
    env.run(["bots/starter/main.py", "bots/random_hold/main.py"])
    final = env.steps[-1]
    assert final[0].status == "DONE"
    assert final[1].status == "DONE"
    assert final[0].reward == 1
    assert final[1].reward == -1


def test_scheduler_runs_rotated_smoke_tournament(tmp_path: Path):
    config = {
        "label": "pytest_smoke",
        "seeds": [1],
        "workers": 1,
        "matchups": [
            {
                "name": "starter_vs_hold",
                "agents": ["bots/starter/main.py", "bots/random_hold/main.py"],
                "player_count": 2,
                "rotate_slots": True,
            }
        ],
    }
    run_dir = Path(run_tournament_from_config(config, out_dir=tmp_path))
    summary = run_dir / "summary.csv"
    assert summary.exists()
    assert "starter_vs_hold" in summary.read_text()


def test_scheduler_exports_viewer_replays_when_configured(tmp_path: Path):
    config = {
        "label": "pytest_replay",
        "seeds": [1],
        "workers": 1,
        "export_viewer_replays": True,
        "matchups": [
            {
                "name": "starter_vs_hold",
                "agents": ["bots/starter/main.py", "bots/random_hold/main.py"],
                "player_count": 2,
                "rotate_slots": False,
            }
        ],
    }
    run_dir = Path(run_tournament_from_config(config, out_dir=tmp_path))
    replays = list((run_dir / "replays").glob("*.viewer.json"))
    assert len(replays) == 1
    text = replays[0].read_text(encoding="utf-8")
    assert '"frames"' in text
    assert "starter_vs_hold" in text

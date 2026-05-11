from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from src.orbitlab.issues import Issue
from src.orbitlab.replay import build_viewer_replay, merge_replay_issues, write_viewer_replay


def _fake_state(observation: dict, action=None):
    return SimpleNamespace(observation=observation, action=action)


def test_build_viewer_replay_exports_frames_metrics_and_issues():
    env = SimpleNamespace(
        steps=[
            [
                _fake_state(
                    {
                        "planets": [
                            [0, 0, 20.0, 30.0, 2.0, 10.0, 3],
                            [1, 1, 80.0, 70.0, 2.0, 20.0, 4],
                            [2, -1, 50.0, 20.0, 1.0, 5.0, 1],
                        ],
                        "fleets": [[0, 0, 25.0, 30.0, 0.0, 0, 6]],
                        "comets": [{"planet_ids": [2], "paths": [[[50.0, 20.0], [54.0, 22.0]]], "path_index": 0}],
                        "comet_planet_ids": [2],
                    },
                    action=[[0, 0.0, 6]],
                ),
                _fake_state({"planets": [], "fleets": []}, action=[]),
            ]
        ]
    )
    match = {
        "match_id": "m1",
        "run_id": "r1",
        "matchup": "a_vs_b",
        "seed": 42,
        "player_count": 2,
        "agents": ["a.py", "b.py"],
        "rewards": [1, -1],
        "statuses": ["DONE", "DONE"],
        "winner_slot": 0,
    }

    replay = build_viewer_replay(
        match,
        env,
        issues=[Issue("slow_expansion", "P2", "Still one planet", "m1", step=60, slot=0)],
        notes=[{"step": 0, "category": "expansion", "text": "Good first launch"}],
    )

    assert replay["schema_version"] == 1
    assert replay["board"]["sun_radius"] == 10.0
    assert replay["frames"][0]["planets"][0][1] == 0
    assert replay["frames"][0]["fleets"][0][6] == 6
    assert replay["frames"][0]["metrics"][0]["total_ships"] == 16.0
    assert replay["frames"][0]["metrics"][1]["production"] == 4
    assert replay["frames"][0]["actions"][0] == [[0, 0.0, 6]]
    assert replay["issues"][0]["detector"] == "slow_expansion"
    assert replay["notes"][0]["text"] == "Good first launch"


def test_write_viewer_replay_creates_json_file(tmp_path: Path):
    env = SimpleNamespace(steps=[[_fake_state({"planets": [], "fleets": [], "comets": [], "comet_planet_ids": []})]])
    match = {"match_id": "m1", "seed": 1, "player_count": 2, "agents": ["a", "b"]}

    out_path = write_viewer_replay(tmp_path / "viewer.json", match, env)

    assert out_path.exists()
    assert json.loads(out_path.read_text(encoding="utf-8"))["match_id"] == "m1"


def test_build_viewer_replay_adds_automatic_analysis_issues():
    env = SimpleNamespace(
        steps=[
            [
                _fake_state(
                    {
                        "planets": [[0, 0, 25.0, 50.0, 2.0, 30.0, 3]],
                        "fleets": [],
                        "comets": [],
                        "comet_planet_ids": [],
                    },
                    action=[[0, 0.0, 10]],
                ),
                _fake_state({"planets": [[0, 0, 25.0, 50.0, 2.0, 30.0, 3]], "fleets": []}, action=[]),
            ]
        ]
    )
    match = {"match_id": "m1", "seed": 1, "player_count": 2, "agents": ["a", "b"]}

    replay = build_viewer_replay(match, env)

    assert replay["analysis"]["detector_counts"]["bad_launch_sun_lane"] == 1
    assert any(issue["detector"] == "bad_launch_sun_lane" for issue in replay["issues"])
    assert replay["frames"][0]["derived"]["leader_slot"] == 0


def test_merge_replay_issues_updates_existing_replay(tmp_path: Path):
    env = SimpleNamespace(steps=[[_fake_state({"planets": [], "fleets": [], "comets": [], "comet_planet_ids": []})]])
    match = {"match_id": "m1", "seed": 1, "player_count": 2, "agents": ["a", "b"]}
    out_path = write_viewer_replay(tmp_path / "viewer.json", match, env)

    merge_replay_issues(out_path, [Issue("crash", "P0", "Slot died", "m1", step=2, slot=1)])

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["issues"][0]["detector"] == "crash"
    assert payload["issues"][0]["slot"] == 1

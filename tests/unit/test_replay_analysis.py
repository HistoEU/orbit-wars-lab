from src.orbitlab.replay_analysis import analyze_replay_payload, build_replay_analysis_summary


def _frame(step, planets, fleets=None, actions=None, comet_planet_ids=None):
    fleets = fleets or []
    actions = actions if actions is not None else [[], []]
    comet_planet_ids = comet_planet_ids or []
    metrics = []
    for slot in [0, 1]:
        owned_planets = [planet for planet in planets if planet[1] == slot]
        owned_fleets = [fleet for fleet in fleets if fleet[1] == slot]
        ships_on_planets = sum(planet[5] for planet in owned_planets)
        ships_in_fleets = sum(fleet[6] for fleet in owned_fleets)
        metrics.append(
            {
                "slot": slot,
                "planets": len(owned_planets),
                "ships_on_planets": ships_on_planets,
                "ships_in_fleets": ships_in_fleets,
                "total_ships": ships_on_planets + ships_in_fleets,
                "production": sum(planet[6] for planet in owned_planets),
                "fleets": len(owned_fleets),
            }
        )
    return {
        "step": step,
        "planets": planets,
        "fleets": fleets,
        "comets": [],
        "comet_planet_ids": comet_planet_ids,
        "actions": actions,
        "metrics": metrics,
    }


def test_flags_bad_launch_lane_through_sun():
    replay = {
        "match_id": "m1",
        "player_count": 2,
        "frames": [_frame(0, [[0, 0, 25.0, 50.0, 2.0, 30.0, 3]], actions=[[[0, 0.0, 10]], []])],
    }

    issues = analyze_replay_payload(replay)

    issue = next(issue for issue in issues if issue.detector == "bad_launch_sun_lane")
    assert issue.step == 0
    assert issue.slot == 0
    assert issue.evidence["planet_id"] == 0
    assert issue.evidence["ships"] == 10


def test_bad_launch_ignores_safe_planet_collision_before_sun():
    replay = {
        "match_id": "m1",
        "player_count": 2,
        "frames": [
            _frame(
                0,
                [
                    [0, 0, 25.0, 50.0, 2.0, 30.0, 3],
                    [2, -1, 33.0, 50.0, 3.0, 8.0, 2],
                ],
                actions=[[[0, 0.0, 10]], []],
            )
        ],
    }

    issues = analyze_replay_payload(replay)

    assert not any(issue.detector == "bad_launch_sun_lane" for issue in issues)


def test_flags_sun_death_when_fleet_disappears_on_sun_crossing_segment():
    replay = {
        "match_id": "m1",
        "player_count": 2,
        "frames": [
            _frame(0, [[0, 0, 20.0, 20.0, 2.0, 20.0, 3]], fleets=[[7, 0, 39.0, 50.0, 0.0, 0, 20]]),
            _frame(1, [[0, 0, 20.0, 20.0, 2.0, 23.0, 3]], fleets=[]),
        ],
    }

    issues = analyze_replay_payload(replay)

    issue = next(issue for issue in issues if issue.detector == "sun_death")
    assert issue.step == 0
    assert issue.slot == 0
    assert issue.evidence["fleet_id"] == 7


def test_flags_missed_comet_window_when_capturable_neutral_comet_is_ignored():
    replay = {
        "match_id": "m1",
        "player_count": 2,
        "frames": [
            _frame(
                50,
                [
                    [0, 0, 35.0, 50.0, 2.0, 45.0, 4],
                    [8, -1, 55.0, 50.0, 1.0, 8.0, 1],
                ],
                comet_planet_ids=[8],
            )
        ],
    }

    issues = analyze_replay_payload(replay)

    issue = next(issue for issue in issues if issue.detector == "missed_comet_window")
    assert issue.step == 50
    assert issue.slot == 0
    assert issue.evidence["comet_id"] == 8


def test_flags_slow_expansion_from_replay_metrics():
    replay = {
        "match_id": "m1",
        "player_count": 2,
        "frames": [
            _frame(0, [[0, 0, 20.0, 20.0, 2.0, 10.0, 3], [1, 1, 80.0, 80.0, 2.0, 10.0, 3]]),
            _frame(60, [[0, 0, 20.0, 20.0, 2.0, 70.0, 3], [1, 1, 80.0, 80.0, 2.0, 40.0, 3]]),
        ],
    }

    issues = analyze_replay_payload(replay)

    assert any(issue.detector == "slow_expansion" and issue.slot == 0 for issue in issues)


def test_flags_idle_overstock_on_high_value_planet_without_launches():
    frames = []
    for step in range(8):
        frames.append(_frame(step, [[0, 0, 25.0, 25.0, 2.0, 85.0 + step, 5]], actions=[[], []]))
    replay = {"match_id": "m1", "player_count": 2, "frames": frames}

    issues = analyze_replay_payload(replay)

    issue = next(issue for issue in issues if issue.detector == "idle_overstock")
    assert issue.slot == 0
    assert issue.evidence["planet_id"] == 0
    assert issue.evidence["idle_frames"] == 8


def test_build_replay_analysis_summary_counts_by_severity_detector_and_step():
    replay = {
        "match_id": "m1",
        "player_count": 2,
        "frames": [_frame(0, [[0, 0, 25.0, 50.0, 2.0, 30.0, 3]], actions=[[[0, 0.0, 10]], []])],
    }
    issues = analyze_replay_payload(replay)

    summary = build_replay_analysis_summary(replay, issues)

    assert summary["total_issues"] >= 1
    assert summary["detector_counts"]["bad_launch_sun_lane"] == 1
    assert summary["severity_counts"]["P1"] == 1
    assert summary["issue_counts_by_step"]["0"] == 1


def test_flags_fleet_disappeared_without_capture_as_tactical_loss():
    replay = {
        "match_id": "m1",
        "player_count": 2,
        "frames": [
            _frame(10, [[0, 0, 20.0, 20.0, 2.0, 20.0, 3]], fleets=[[9, 0, 15.0, 15.0, 0.0, 0, 12]]),
            _frame(11, [[0, 0, 20.0, 20.0, 2.0, 23.0, 3]], fleets=[]),
        ],
    }

    issues = analyze_replay_payload(replay)

    issue = next(issue for issue in issues if issue.detector == "fleet_disappeared_without_capture")
    assert issue.slot == 0
    assert issue.evidence["fleet_id"] == 9


def test_flags_late_trailing_no_pressure():
    replay = {
        "match_id": "m1",
        "player_count": 2,
        "frames": [
            {
                "step": 360,
                "planets": [],
                "fleets": [],
                "comet_planet_ids": [],
                "actions": [[], []],
                "metrics": [
                    {"slot": 0, "planets": 2, "ships_on_planets": 45, "ships_in_fleets": 0, "total_ships": 45, "production": 4, "fleets": 0},
                    {"slot": 1, "planets": 4, "ships_on_planets": 90, "ships_in_fleets": 10, "total_ships": 100, "production": 8, "fleets": 2},
                ],
            }
        ],
    }

    issues = analyze_replay_payload(replay)

    assert any(issue.detector == "late_trailing_no_pressure" and issue.slot == 0 for issue in issues)


def test_flags_overdefended_low_production_planet():
    replay = {
        "match_id": "m1",
        "player_count": 2,
        "frames": [
            _frame(
                180,
                [
                    [0, 0, 20.0, 20.0, 1.0, 72.0, 1],
                    [1, 1, 60.0, 20.0, 1.0, 20.0, 3],
                    [2, 1, 65.0, 25.0, 1.0, 20.0, 3],
                ],
            )
        ],
    }

    issues = analyze_replay_payload(replay)

    issue = next(issue for issue in issues if issue.detector == "overdefended_low_production")
    assert issue.slot == 0
    assert issue.evidence["planet_id"] == 0

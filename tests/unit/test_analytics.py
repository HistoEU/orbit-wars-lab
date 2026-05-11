from src.orbitlab.analytics import (
    build_leaderboard,
    build_matchup_matrix,
    compare_agent_summaries,
    summarize_phase_metrics,
    wilson_interval,
)


def test_wilson_interval_bounds_zero_games():
    low, high = wilson_interval(0, 0)
    assert low == 0.0
    assert high == 0.0


def test_build_leaderboard_tracks_slots_rewards_and_confidence():
    matches = [
        {
            "match_id": "m1",
            "agents": ["candidate", "baseline"],
            "rewards": [1, -1],
            "winner_agent": "candidate",
            "steps": 300,
        },
        {
            "match_id": "m2",
            "agents": ["baseline", "candidate"],
            "rewards": [-1, 1],
            "winner_agent": "candidate",
            "steps": 500,
        },
        {
            "match_id": "m3",
            "agents": ["candidate", "baseline"],
            "rewards": [-1, 1],
            "winner_agent": "baseline",
            "steps": 400,
        },
    ]

    rows = build_leaderboard(matches)

    candidate = rows[0]
    assert candidate["agent"] == "candidate"
    assert candidate["games"] == 3
    assert candidate["wins"] == 2
    assert candidate["losses"] == 1
    assert candidate["avg_reward"] == 1 / 3
    assert candidate["slot_0_games"] == 2
    assert candidate["slot_1_games"] == 1
    assert 0.0 < candidate["win_rate_ci_low"] < candidate["win_rate"]
    assert candidate["win_rate"] < candidate["win_rate_ci_high"] <= 1.0


def test_build_matchup_matrix_aggregates_head_to_head_records():
    matches = [
        {"match_id": "m1", "matchup": "cand_vs_base", "agents": ["candidate", "baseline"], "winner_agent": "candidate"},
        {"match_id": "m2", "matchup": "cand_vs_base", "agents": ["baseline", "candidate"], "winner_agent": "baseline"},
        {"match_id": "m3", "matchup": "cand_vs_base", "agents": ["candidate", "baseline"], "winner_agent": None},
    ]

    rows = build_matchup_matrix(matches)

    candidate = next(row for row in rows if row["agent"] == "candidate")
    assert candidate["matchup"] == "cand_vs_base"
    assert candidate["games"] == 3
    assert candidate["wins"] == 1
    assert candidate["losses"] == 1
    assert candidate["draws"] == 1


def test_summarize_phase_metrics_maps_slots_to_agents():
    matches = [
        {"match_id": "m1", "agents": ["candidate", "baseline"]},
        {"match_id": "m2", "agents": ["baseline", "candidate"]},
    ]
    metrics = [
        {"match_id": "m1", "step": 20, "slot": 0, "planets": 3, "ships_on_planets": 50, "ships_in_fleets": 10, "production": 3, "fleets": 1},
        {"match_id": "m1", "step": 160, "slot": 0, "planets": 5, "ships_on_planets": 90, "ships_in_fleets": 30, "production": 5, "fleets": 2},
        {"match_id": "m2", "step": 360, "slot": 1, "planets": 7, "ships_on_planets": 140, "ships_in_fleets": 40, "production": 7, "fleets": 3},
    ]

    rows = summarize_phase_metrics(metrics, matches, phase_edges=(100, 300))

    early = next(row for row in rows if row["agent"] == "candidate" and row["phase"] == "early")
    mid = next(row for row in rows if row["agent"] == "candidate" and row["phase"] == "mid")
    late = next(row for row in rows if row["agent"] == "candidate" and row["phase"] == "late")
    assert early["samples"] == 1
    assert early["avg_total_ships"] == 60.0
    assert mid["avg_planets"] == 5.0
    assert late["avg_fleets"] == 3.0


def test_compare_agent_summaries_reports_deltas_by_agent():
    baseline = [
        {"agent": "candidate", "games": 10, "wins": 5, "win_rate": 0.5, "avg_reward": 0.0},
        {"agent": "baseline", "games": 10, "wins": 5, "win_rate": 0.5, "avg_reward": 0.0},
    ]
    candidate = [
        {"agent": "candidate", "games": 12, "wins": 8, "win_rate": 2 / 3, "avg_reward": 0.25},
    ]

    rows = compare_agent_summaries(baseline, candidate)

    assert rows == [
        {
            "agent": "candidate",
            "baseline_games": 10,
            "candidate_games": 12,
            "baseline_win_rate": 0.5,
            "candidate_win_rate": 2 / 3,
            "win_rate_delta": 2 / 3 - 0.5,
            "baseline_avg_reward": 0.0,
            "candidate_avg_reward": 0.25,
            "avg_reward_delta": 0.25,
        }
    ]

from src.orbitlab.detectors import detect_crashes, detect_slot_bias, detect_timeout_or_slow_match


def test_detect_crashes_emits_p0_for_non_done_status():
    issues = detect_crashes({"match_id": "m1", "statuses": ["DONE", "ERROR"]})
    assert issues[0].severity == "P0"
    assert issues[0].slot == 1


def test_detect_slot_bias_emits_signal_after_enough_games():
    matches = []
    for i in range(20):
        matches.append({"match_id": f"w{i}", "agents": ["focus", "other"], "winner_agent": "focus"})
        matches.append({"match_id": f"l{i}", "agents": ["other", "focus"], "winner_agent": "other"})
    issues = detect_slot_bias(matches, "focus", min_games_per_slot=20)
    assert issues
    assert issues[0].severity == "P3"


def test_detect_timeout_or_slow_match():
    issues = detect_timeout_or_slow_match({"match_id": "m1", "elapsed_seconds": 3.5}, max_elapsed_seconds=1.0)
    assert issues[0].severity == "P1"

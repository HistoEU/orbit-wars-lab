from pathlib import Path

from src.orbitlab.storage import init_db, insert_issue, insert_match, read_issues, read_matches


def test_match_roundtrip(tmp_path: Path):
    db_path = tmp_path / "results.sqlite"
    init_db(db_path)
    insert_match(
        db_path,
        {
            "match_id": "m1",
            "run_id": "r1",
            "matchup": "a_vs_b",
            "seed": 42,
            "player_count": 2,
            "agents": ["a.py", "b.py"],
            "rewards": [1, -1],
            "statuses": ["DONE", "DONE"],
            "steps": 500,
            "winner_slot": 0,
            "elapsed_seconds": 0.25,
            "replay_path": None,
            "error_text": None,
        },
    )
    rows = read_matches(db_path)
    assert rows[0]["seed"] == 42
    assert rows[0]["rewards"] == [1, -1]
    assert rows[0]["winner_agent"] == "a.py"


def test_issue_roundtrip(tmp_path: Path):
    db_path = tmp_path / "results.sqlite"
    init_db(db_path)
    insert_issue(
        db_path,
        {
            "issue_id": "i1",
            "match_id": "m1",
            "detector": "crash",
            "severity": "P0",
            "step": None,
            "slot": 1,
            "message": "Agent crashed",
            "evidence": {"status": "ERROR"},
        },
    )
    rows = read_issues(db_path)
    assert rows[0]["evidence"] == {"status": "ERROR"}

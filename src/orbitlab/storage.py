from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path) -> None:
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                label TEXT NOT NULL,
                config_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bots (
                bot_id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS matches (
                match_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                matchup TEXT NOT NULL,
                seed INTEGER NOT NULL,
                player_count INTEGER NOT NULL,
                slots_json TEXT NOT NULL,
                rewards_json TEXT NOT NULL,
                statuses_json TEXT NOT NULL,
                steps INTEGER NOT NULL,
                winner_slot INTEGER,
                elapsed_seconds REAL NOT NULL,
                replay_path TEXT,
                error_text TEXT
            );

            CREATE TABLE IF NOT EXISTS turn_metrics (
                match_id TEXT NOT NULL,
                step INTEGER NOT NULL,
                slot INTEGER NOT NULL,
                planets INTEGER NOT NULL,
                ships_on_planets REAL NOT NULL,
                ships_in_fleets REAL NOT NULL,
                production INTEGER NOT NULL,
                fleets INTEGER NOT NULL,
                PRIMARY KEY(match_id, step, slot)
            );

            CREATE TABLE IF NOT EXISTS issues (
                issue_id TEXT PRIMARY KEY,
                match_id TEXT NOT NULL,
                detector TEXT NOT NULL,
                severity TEXT NOT NULL,
                step INTEGER,
                slot INTEGER,
                message TEXT NOT NULL,
                evidence_json TEXT NOT NULL
            );
            """
        )


def insert_run(db_path: str | Path, run_id: str, created_at: str, label: str, config: dict[str, Any]) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO runs(run_id, created_at, label, config_json) VALUES (?, ?, ?, ?)",
            (run_id, created_at, label, json.dumps(config, sort_keys=True)),
        )


def insert_match(db_path: str | Path, match: dict[str, Any]) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO matches(
                match_id, run_id, matchup, seed, player_count, slots_json,
                rewards_json, statuses_json, steps, winner_slot, elapsed_seconds,
                replay_path, error_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                match["match_id"],
                match.get("run_id", ""),
                match.get("matchup", ""),
                int(match["seed"]),
                int(match["player_count"]),
                json.dumps(match.get("agents", [])),
                json.dumps(match.get("rewards", [])),
                json.dumps(match.get("statuses", [])),
                int(match.get("steps", 0)),
                match.get("winner_slot"),
                float(match.get("elapsed_seconds", 0.0)),
                match.get("replay_path"),
                match.get("error_text"),
            ),
        )


def insert_turn_metric(db_path: str | Path, metric: dict[str, Any]) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO turn_metrics(
                match_id, step, slot, planets, ships_on_planets,
                ships_in_fleets, production, fleets
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metric["match_id"],
                int(metric["step"]),
                int(metric["slot"]),
                int(metric["planets"]),
                float(metric["ships_on_planets"]),
                float(metric["ships_in_fleets"]),
                int(metric["production"]),
                int(metric["fleets"]),
            ),
        )


def insert_issue(db_path: str | Path, issue: dict[str, Any]) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO issues(
                issue_id, match_id, detector, severity, step, slot, message, evidence_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                issue["issue_id"],
                issue["match_id"],
                issue["detector"],
                issue["severity"],
                issue.get("step"),
                issue.get("slot"),
                issue["message"],
                json.dumps(issue.get("evidence", {}), sort_keys=True),
            ),
        )


def read_matches(db_path: str | Path) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM matches ORDER BY match_id").fetchall()
    matches = []
    for row in rows:
        agents = json.loads(row["slots_json"])
        rewards = json.loads(row["rewards_json"])
        statuses = json.loads(row["statuses_json"])
        winner_slot = row["winner_slot"]
        matches.append(
            {
                "match_id": row["match_id"],
                "run_id": row["run_id"],
                "matchup": row["matchup"],
                "seed": row["seed"],
                "player_count": row["player_count"],
                "agents": agents,
                "rewards": rewards,
                "statuses": statuses,
                "steps": row["steps"],
                "winner_slot": winner_slot,
                "winner_agent": agents[winner_slot] if winner_slot is not None and 0 <= winner_slot < len(agents) else None,
                "elapsed_seconds": row["elapsed_seconds"],
                "replay_path": row["replay_path"],
                "error_text": row["error_text"],
            }
        )
    return matches


def read_issues(db_path: str | Path) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM issues ORDER BY severity, detector, issue_id").fetchall()
    return [
        {
            "issue_id": row["issue_id"],
            "match_id": row["match_id"],
            "detector": row["detector"],
            "severity": row["severity"],
            "step": row["step"],
            "slot": row["slot"],
            "message": row["message"],
            "evidence": json.loads(row["evidence_json"]),
        }
        for row in rows
    ]


def write_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

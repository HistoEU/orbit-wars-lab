from __future__ import annotations

from pathlib import Path


def _bot_label(path: str) -> str:
    parts = Path(path).parts
    if len(parts) >= 2:
        return parts[-2]
    return Path(path).stem


def build_compare_config(
    candidate: str,
    baseline: str,
    seeds: list[int],
    workers: int = 1,
    export_viewer_replays: bool = False,
) -> dict:
    return {
        "label": f"compare_{_bot_label(candidate)}_vs_{_bot_label(baseline)}",
        "seeds": [int(seed) for seed in seeds],
        "workers": int(workers),
        "export_viewer_replays": bool(export_viewer_replays),
        "matchups": [
            {
                "name": "candidate_vs_baseline",
                "agents": [candidate, baseline],
                "player_count": 2,
                "rotate_slots": True,
            }
        ],
    }

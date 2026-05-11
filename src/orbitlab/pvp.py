from __future__ import annotations


def build_pvp_config(
    agents: list[str],
    seeds: list[int],
    player_count: int | None = None,
    workers: int = 1,
    export_viewer_replays: bool = False,
) -> dict:
    count = int(player_count or len(agents))
    if count not in (2, 4):
        raise ValueError("Orbit Wars PvP supports 2 or 4 players.")
    if len(agents) != count:
        raise ValueError(f"PvP {count}P requires exactly {count} agents.")
    return {
        "label": f"pvp_{count}p",
        "seeds": [int(seed) for seed in seeds],
        "workers": int(workers),
        "export_viewer_replays": bool(export_viewer_replays),
        "matchups": [
            {
                "name": f"pvp_{count}p",
                "agents": list(agents),
                "player_count": count,
                "rotate_slots": True,
            }
        ],
    }

from __future__ import annotations

from collections import defaultdict


def resolve_combat(owner: int, garrison: float, arrivals: list[tuple[int, int]]) -> tuple[int, float]:
    grouped: dict[int, int] = defaultdict(int)
    for arrival_owner, ships in arrivals:
        if ships > 0:
            grouped[int(arrival_owner)] += int(ships)

    if not grouped:
        return owner, max(0.0, garrison)

    ranked = sorted(grouped.items(), key=lambda item: item[1], reverse=True)
    top_owner, top_ships = ranked[0]
    if len(ranked) > 1:
        second_ships = ranked[1][1]
        if top_ships == second_ships:
            return owner, max(0.0, garrison)
        survivor_owner = top_owner
        survivor_ships = top_ships - second_ships
    else:
        survivor_owner = top_owner
        survivor_ships = top_ships

    if survivor_owner == owner:
        return owner, garrison + survivor_ships

    remaining = garrison - survivor_ships
    if remaining < 0:
        return survivor_owner, -remaining
    return owner, remaining

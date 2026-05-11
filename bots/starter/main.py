import math
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet


def agent(obs, config=None):
    moves = []
    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    planets = [Planet(*p) for p in raw_planets]
    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]

    if not targets:
        return moves

    for mine in my_planets:
        nearest = None
        min_dist = float("inf")
        for target in targets:
            dist = math.sqrt((mine.x - target.x) ** 2 + (mine.y - target.y) ** 2)
            if dist < min_dist:
                min_dist = dist
                nearest = target

        if nearest is None:
            continue

        ships_needed = int(nearest.ships) + 1
        if mine.ships >= ships_needed:
            angle = math.atan2(nearest.y - mine.y, nearest.x - mine.x)
            moves.append([mine.id, angle, ships_needed])

    return moves

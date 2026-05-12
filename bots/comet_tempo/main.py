import math


BOARD_SIZE = 100.0
CENTER = 50.0
SUN_RADIUS = 10.0
SUN_SAFETY_MARGIN = 0.5
MAX_SPEED = 6.0
LAUNCH_CLEARANCE = 0.1
ANGLE_OFFSETS = [0.0, -0.06, 0.06, -0.12, 0.12, -0.20, 0.20]

COMET_LIFE_WEIGHT = 1.8
DENIAL_WEIGHT = 8.0
FORWARD_BASE_WEIGHT = 3.0
SHIP_CACHE_WEIGHT = 0.4
TRAVEL_WEIGHT = 1.2
SOURCE_WEAKENING_WEIGHT = 2.0
MIN_LIFE_AFTER_CAPTURE = 10


class PlanetView:
    __slots__ = ("id", "owner", "x", "y", "radius", "ships", "production", "is_comet")

    def __init__(self, planet_id, owner, x, y, radius, ships, production, is_comet=False):
        self.id = int(planet_id)
        self.owner = int(owner)
        self.x = float(x)
        self.y = float(y)
        self.radius = float(radius)
        self.ships = float(ships)
        self.production = int(production)
        self.is_comet = bool(is_comet)


class FleetView:
    __slots__ = ("id", "owner", "x", "y", "angle", "from_planet_id", "ships")

    def __init__(self, fleet_id, owner, x, y, angle, from_planet_id, ships):
        self.id = int(fleet_id)
        self.owner = int(owner)
        self.x = float(x)
        self.y = float(y)
        self.angle = float(angle)
        self.from_planet_id = int(from_planet_id)
        self.ships = int(ships)


def read_field(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_comets(obs):
    meta = {}
    groups = list(read_field(obs, "comets", []) or [])
    if not groups and read_field(obs, "comet_planet_ids", None) is not None and read_field(obs, "paths", None) is not None:
        groups = [
            {
                "planet_ids": list(read_field(obs, "comet_planet_ids", []) or []),
                "paths": list(read_field(obs, "paths", []) or []),
                "path_index": read_field(obs, "path_index", 0),
            }
        ]
    for group in groups:
        planet_ids = [as_int(x) for x in (group.get("planet_ids", []) or [])]
        paths = group.get("paths", []) or []
        raw_index = group.get("path_index", 0)
        for index, planet_id in enumerate(planet_ids):
            if index >= len(paths):
                continue
            path = paths[index] or []
            if isinstance(raw_index, dict):
                path_index = as_int(raw_index.get(planet_id, raw_index.get(str(planet_id), 0)), 0)
            else:
                path_index = as_int(raw_index, 0)
            remaining = max(0, len(path) - path_index)
            meta[planet_id] = {
                "path": path,
                "path_index": path_index,
                "remaining_life": remaining,
            }
    return meta


def comet_future_position(comet_id, meta, turns):
    comet = meta.get(int(comet_id))
    if not comet:
        return None
    path = comet.get("path", [])
    index = int(comet.get("path_index", 0)) + int(math.ceil(turns))
    if index < 0 or index >= len(path):
        return None
    point = path[index]
    return float(point[0]), float(point[1])


def parse_planet(raw, comet_ids=None):
    comet_ids = comet_ids or set()
    if isinstance(raw, (list, tuple)):
        return PlanetView(raw[0], raw[1], raw[2], raw[3], raw[4], raw[5], raw[6], int(raw[0]) in comet_ids)
    planet_id = read_field(raw, "id", 0)
    return PlanetView(
        planet_id,
        read_field(raw, "owner", -1),
        read_field(raw, "x", 0.0),
        read_field(raw, "y", 0.0),
        read_field(raw, "radius", 0.0),
        read_field(raw, "ships", 0.0),
        read_field(raw, "production", 0),
        int(planet_id) in comet_ids,
    )


def parse_fleet(raw):
    if isinstance(raw, (list, tuple)):
        return FleetView(raw[0], raw[1], raw[2], raw[3], raw[4], raw[5], raw[6])
    return FleetView(
        read_field(raw, "id", 0),
        read_field(raw, "owner", -1),
        read_field(raw, "x", 0.0),
        read_field(raw, "y", 0.0),
        read_field(raw, "angle", 0.0),
        read_field(raw, "from_planet_id", 0),
        read_field(raw, "ships", 0),
    )


def parse_state(obs):
    player = as_int(read_field(obs, "player", 0), 0)
    comet_meta = parse_comets(obs)
    comet_ids = set(comet_meta)
    comet_ids.update(as_int(x) for x in (read_field(obs, "comet_planet_ids", []) or []))
    planets = [parse_planet(p, comet_ids) for p in (read_field(obs, "planets", []) or [])]
    fleets = [parse_fleet(f) for f in (read_field(obs, "fleets", []) or [])]
    return {
        "player": player,
        "step": as_int(read_field(obs, "step", 0), 0),
        "planets": planets,
        "fleets": fleets,
        "comet_meta": comet_meta,
        "mine": [p for p in planets if p.owner == player],
        "enemies": [p for p in planets if p.owner >= 0 and p.owner != player],
        "neutral": [p for p in planets if p.owner < 0],
        "comets": [p for p in planets if p.is_comet],
        "targets": [p for p in planets if p.owner != player],
    }


def dist_xy(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def distance(a, b):
    return dist_xy(a.x, a.y, b.x, b.y)


def fleet_speed(ships):
    ships = max(1.0, float(ships))
    ratio = math.log(ships) / math.log(1000.0)
    ratio = max(0.0, min(1.0, ratio))
    return 1.0 + (MAX_SPEED - 1.0) * (ratio**1.5)


def launch_point(source, angle):
    clearance = source.radius + LAUNCH_CLEARANCE
    return source.x + math.cos(angle) * clearance, source.y + math.sin(angle) * clearance


def segment_progress_to_circle(cx, cy, radius, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    fx = x1 - cx
    fy = y1 - cy
    a = dx * dx + dy * dy
    b = 2.0 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - radius * radius
    if a <= 1e-12:
        return 0.0 if c <= 0 else None
    disc = b * b - 4.0 * a * c
    if disc < 0:
        return None
    root = math.sqrt(disc)
    candidates = [(-b - root) / (2.0 * a), (-b + root) / (2.0 * a)]
    valid = [t for t in candidates if 0.0 <= t <= 1.0]
    return min(valid) if valid else None


def plan_route_to_point(source, target, ships, aim_x, aim_y):
    base = math.atan2(aim_y - source.y, aim_x - source.x)
    best = None
    for offset in ANGLE_OFFSETS:
        angle = base + offset
        sx, sy = launch_point(source, angle)
        far_x = sx + math.cos(angle) * BOARD_SIZE * 2
        far_y = sy + math.sin(angle) * BOARD_SIZE * 2
        target_progress = segment_progress_to_circle(target.x, target.y, target.radius, sx, sy, far_x, far_y)
        if target_progress is None:
            continue
        sun_progress = segment_progress_to_circle(
            CENTER,
            CENTER,
            SUN_RADIUS + SUN_SAFETY_MARGIN,
            sx,
            sy,
            far_x,
            far_y,
        )
        if sun_progress is not None and sun_progress < target_progress:
            continue
        hit_distance = target_progress * BOARD_SIZE * 2
        turns = max(1, int(math.ceil(hit_distance / fleet_speed(ships))))
        risk = 0.0 if abs(offset) < 1e-12 else abs(offset) * 10.0
        route = {"angle": float(angle), "travel_turns": turns, "risk": risk}
        if best is None or (route["risk"], route["travel_turns"]) < (best["risk"], best["travel_turns"]):
            best = route
    return best


def plan_route(source, target, ships):
    return plan_route_to_point(source, target, ships, target.x, target.y)


def compute_reserve(source, state):
    if state.get("step", 0) < 45:
        return max(5.0, source.production)
    return max(8.0, source.production * 1.75)


def capture_ships(target, travel_turns):
    margin = max(2.0, target.production * 1.5, target.ships * 0.08)
    growth = 0.0 if target.owner < 0 else max(0, target.production) * travel_turns
    return int(math.ceil(target.ships + growth + margin))


def enemy_denial_value(comet, state, meta):
    if not state.get("enemies"):
        return 0.0
    best_enemy = min(state["enemies"], key=lambda enemy: distance(enemy, comet))
    if best_enemy.ships < comet.ships + 2:
        return 0.0
    enemy_turns = max(1, int(math.ceil(distance(best_enemy, comet) / fleet_speed(max(1, comet.ships + 2)))))
    remaining = meta.get(comet.id, {}).get("remaining_life", 0)
    if enemy_turns >= remaining:
        return 0.0
    return min(25.0, (remaining - enemy_turns) * 0.8 + comet.production * DENIAL_WEIGHT)


def score_comet_candidate(source, comet, state, meta):
    rough_route = plan_route(source, comet, max(1, int(comet.ships + 2)))
    if rough_route is None:
        return {"score": -9999.0, "reason": "unsafe_route", "ships": 0, "route": None}
    predicted = comet_future_position(comet.id, meta, rough_route["travel_turns"])
    aim_x, aim_y = predicted if predicted is not None else (comet.x, comet.y)
    route = plan_route_to_point(source, comet, max(1, int(comet.ships + 2)), aim_x, aim_y)
    if route is None:
        return {"score": -9999.0, "reason": "unsafe_route", "ships": 0, "route": None}
    ships = capture_ships(comet, route["travel_turns"])
    route = plan_route_to_point(source, comet, ships, aim_x, aim_y)
    if route is None:
        return {"score": -9999.0, "reason": "unsafe_route", "ships": ships, "route": None}
    remaining = meta.get(comet.id, {}).get("remaining_life", 0)
    life_after_capture = remaining - route["travel_turns"]
    if life_after_capture < MIN_LIFE_AFTER_CAPTURE:
        return {"score": -999.0, "reason": "expires_too_soon", "ships": ships, "route": route}
    reserve = compute_reserve(source, state)
    source_weakening = max(0.0, ships - max(0.0, source.ships - reserve)) * SOURCE_WEAKENING_WEIGHT
    forward = 0.0
    if state.get("enemies"):
        nearest_enemy = min(distance(comet, enemy) for enemy in state["enemies"])
        nearest_source_enemy = min(distance(source, enemy) for enemy in state["enemies"])
        forward = max(0.0, nearest_source_enemy - nearest_enemy) / 10.0
    score = (
        life_after_capture * comet.production * COMET_LIFE_WEIGHT
        + enemy_denial_value(comet, state, meta)
        + forward * FORWARD_BASE_WEIGHT
        + comet.ships * SHIP_CACHE_WEIGHT
        - ships
        - route["travel_turns"] * TRAVEL_WEIGHT
        - route["risk"] * 3.0
        - source_weakening
    )
    return {"score": score, "reason": "comet_value", "ships": ships, "route": route}


def phase_comet_budget_fraction(step):
    if step < 60:
        return 0.30
    if step < 300:
        return 0.50
    return 0.25


def plan_comet_launches(state):
    meta = state.get("comet_meta", {})
    proposals = []
    for source in state["mine"]:
        reserve = compute_reserve(source, state)
        surplus = max(0.0, source.ships - reserve)
        budget = int(math.floor(surplus * phase_comet_budget_fraction(state.get("step", 0))))
        if budget <= 0:
            continue
        for comet in state["comets"]:
            if comet.owner == state["player"]:
                continue
            scored = score_comet_candidate(source, comet, state, meta)
            if scored["score"] <= 0:
                continue
            proposals.append((scored["score"], source, comet, scored, budget))
    proposals.sort(key=lambda item: (-item[0], item[3]["route"]["travel_turns"], item[2].id))
    source_spent = {}
    target_planned = {}
    moves = []
    for _score, source, comet, scored, budget in proposals:
        reserve = compute_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve - source_spent.get(source.id, 0)))
        remaining_budget = budget - source_spent.get(source.id, 0)
        remaining_need = scored["ships"] - target_planned.get(comet.id, 0)
        ships = min(surplus, remaining_budget, remaining_need)
        if ships <= 0 or ships < scored["ships"]:
            continue
        route = plan_route(source, comet, ships)
        if route is None:
            continue
        source_spent[source.id] = source_spent.get(source.id, 0) + ships
        target_planned[comet.id] = target_planned.get(comet.id, 0) + ships
        moves.append([source.id, float(route["angle"]), int(ships)])
    return moves


def plan_expansion_fallback(state, reserved_sources=None):
    reserved_sources = reserved_sources or {}
    targets = [p for p in state["neutral"] if not p.is_comet] or [p for p in state["targets"] if not p.is_comet]
    proposals = []
    for source in state["mine"]:
        reserve = compute_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve - reserved_sources.get(source.id, 0)))
        if surplus <= 0:
            continue
        for target in targets:
            rough = max(1, int(target.ships + max(2, target.production * 1.5)))
            route = plan_route(source, target, rough)
            if route is None:
                continue
            ships = capture_ships(target, route["travel_turns"])
            score = target.production * 12.0 - ships - route["travel_turns"] * 0.8
            if score > -10:
                proposals.append((score, source, target, ships, route))
    proposals.sort(key=lambda item: (-item[0], item[4]["travel_turns"], item[2].id))
    moves = []
    source_spent = dict(reserved_sources)
    target_planned = {}
    for _score, source, target, ships_needed, route in proposals:
        reserve = compute_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve - source_spent.get(source.id, 0)))
        remaining = ships_needed - target_planned.get(target.id, 0)
        ships = min(surplus, remaining)
        if ships <= 0:
            continue
        final = plan_route(source, target, ships)
        if final is None:
            continue
        source_spent[source.id] = source_spent.get(source.id, 0) + ships
        target_planned[target.id] = target_planned.get(target.id, 0) + ships
        moves.append([source.id, float(final["angle"]), int(ships)])
    return moves


def plan_moves(state):
    comet_moves = plan_comet_launches(state)
    reserved = {}
    for source_id, _angle, ships in comet_moves:
        reserved[source_id] = reserved.get(source_id, 0) + ships
    return comet_moves + plan_expansion_fallback(state, reserved_sources=reserved)


def agent(obs, config=None):
    try:
        return plan_moves(parse_state(obs))
    except Exception:
        return []

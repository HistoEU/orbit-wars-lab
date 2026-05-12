import math


BOARD_SIZE = 100.0
CENTER = 50.0
SUN_RADIUS = 10.0
SUN_SAFETY_MARGIN = 0.5
MAX_SPEED = 6.0
LAUNCH_CLEARANCE = 0.1
ROTATION_RADIUS_LIMIT = 50.0
ANGLE_OFFSETS = [0.0, -0.06, 0.06, -0.12, 0.12, -0.20, 0.20, -0.30, 0.30]


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


def angle_to(ax, ay, bx, by):
    return math.atan2(by - ay, bx - ax)


def dist_xy(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def distance(a, b):
    return dist_xy(a.x, a.y, b.x, b.y)


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
    comet_ids = {as_int(x) for x in (read_field(obs, "comet_planet_ids", []) or [])}
    planets = [parse_planet(p, comet_ids) for p in (read_field(obs, "planets", []) or [])]
    initial_planets = [parse_planet(p, comet_ids) for p in (read_field(obs, "initial_planets", []) or [])]
    fleets = [parse_fleet(f) for f in (read_field(obs, "fleets", []) or [])]
    owners = {p.owner for p in planets if p.owner >= 0}
    owners.update(f.owner for f in fleets if f.owner >= 0)
    players = list(read_field(obs, "players", []) or [])
    return {
        "player": player,
        "step": as_int(read_field(obs, "step", 0), 0),
        "player_count": len(players) if players else max(2, len(owners)),
        "planets": planets,
        "initial_by_id": {p.id: p for p in initial_planets},
        "fleets": fleets,
        "angular_velocity": as_float(read_field(obs, "angular_velocity", 0.0), 0.0),
        "mine": [p for p in planets if p.owner == player],
        "targets": [p for p in planets if p.owner != player],
        "neutral": [p for p in planets if p.owner < 0],
        "enemies": [p for p in planets if p.owner >= 0 and p.owner != player],
    }


def fleet_speed(ships):
    ships = max(1.0, float(ships))
    ratio = math.log(ships) / math.log(1000.0)
    ratio = max(0.0, min(1.0, ratio))
    return 1.0 + (MAX_SPEED - 1.0) * (ratio**1.5)


def launch_point(source, angle):
    clearance = source.radius + LAUNCH_CLEARANCE
    return source.x + math.cos(angle) * clearance, source.y + math.sin(angle) * clearance


def segment_circle_distance(cx, cy, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return math.hypot(cx - x1, cy - y1)
    t = ((cx - x1) * dx + (cy - y1) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    return math.hypot(cx - (x1 + t * dx), cy - (y1 + t * dy))


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


def orbital_radius(planet):
    return dist_xy(planet.x, planet.y, CENTER, CENTER)


def is_orbiting(planet):
    return orbital_radius(planet) + planet.radius < ROTATION_RADIUS_LIMIT


def predict_orbiting_position(planet, initial_by_id, angular_velocity, turns):
    initial = initial_by_id.get(planet.id, planet)
    if not is_orbiting(initial) or abs(angular_velocity) <= 1e-12:
        return planet.x, planet.y
    radius = orbital_radius(initial)
    current_angle = math.atan2(planet.y - CENTER, planet.x - CENTER)
    future_angle = current_angle + angular_velocity * turns
    return CENTER + radius * math.cos(future_angle), CENTER + radius * math.sin(future_angle)


def _route_for_angle(source, target, ships, angle, reason):
    sx, sy = launch_point(source, angle)
    far_x = sx + math.cos(angle) * BOARD_SIZE * 2
    far_y = sy + math.sin(angle) * BOARD_SIZE * 2
    target_progress = segment_progress_to_circle(target.x, target.y, target.radius, sx, sy, far_x, far_y)
    if target_progress is None:
        return None
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
        return None
    hit_distance = max(0.0, target_progress * BOARD_SIZE * 2)
    travel_turns = max(1, int(math.ceil(hit_distance / fleet_speed(max(ships, 1)))))
    sun_margin = segment_circle_distance(CENTER, CENTER, sx, sy, sx + math.cos(angle) * hit_distance, sy + math.sin(angle) * hit_distance)
    risk = max(0.0, (SUN_RADIUS + SUN_SAFETY_MARGIN + 2.0) - sun_margin)
    return {
        "source_id": source.id,
        "target_id": target.id,
        "angle": float(angle),
        "ships": int(ships),
        "travel_turns": travel_turns,
        "risk": risk,
        "reason": reason,
    }


def plan_route(source, target, ships, allow_offsets=True, initial_by_id=None, angular_velocity=0.0):
    aim_x, aim_y = target.x, target.y
    if initial_by_id and abs(angular_velocity) > 1e-12:
        rough_angle = angle_to(source.x, source.y, target.x, target.y)
        rough = _route_for_angle(source, target, ships, rough_angle, "direct_safe")
        rough_turns = rough["travel_turns"] if rough else max(1, int(math.ceil(distance(source, target) / fleet_speed(ships))))
        aim_x, aim_y = predict_orbiting_position(target, initial_by_id, angular_velocity, rough_turns)
    base_angle = angle_to(source.x, source.y, aim_x, aim_y)
    offsets = ANGLE_OFFSETS if allow_offsets else [0.0]
    routes = []
    for offset in offsets:
        reason = "direct_safe" if abs(offset) <= 1e-12 else "offset_safe"
        route = _route_for_angle(source, target, ships, base_angle + offset, reason)
        if route is not None:
            routes.append(route)
    if not routes:
        return None
    routes.sort(key=lambda route: (route["risk"], route["travel_turns"], 0 if route["reason"] == "direct_safe" else 1))
    best = routes[0]
    if initial_by_id and abs(angular_velocity) > 1e-12 and best["reason"] == "direct_safe":
        best = dict(best)
        best["reason"] = "predicted_safe"
    return best


def compute_reserve(source, state):
    step = state.get("step", 0)
    if step < 45:
        return max(5.0, source.production)
    return max(8.0, source.production * 1.75)


def ships_required(target, travel_turns):
    margin = max(2.0, target.production * 1.5, target.ships * 0.08)
    growth = 0.0 if target.owner < 0 else max(0, target.production) * travel_turns
    return int(math.ceil(target.ships + growth + margin))


def score_route(source, target, route, state):
    production_score = max(0, target.production) * 12.0
    cost = route["ships"] * 1.0 + route["travel_turns"] * 0.8 + route["risk"] * 4.0
    enemy_bonus = 8.0 if target.owner >= 0 else 0.0
    return production_score + enemy_bonus - cost


def candidate_targets(state):
    if state.get("step", 0) < 70 and state["neutral"]:
        return state["neutral"]
    return state["targets"]


def opening_first_capture(state):
    if state.get("step", 0) > 60 or len(state.get("mine", [])) != 1 or not state.get("neutral", []):
        return []
    source = state["mine"][0]
    candidates = []
    for target in state["neutral"]:
        if target.is_comet:
            continue
        ships = int(math.floor(target.ships)) + 1
        if source.ships < ships + 1:
            continue
        route = plan_route(
            source,
            target,
            ships,
            allow_offsets=True,
            initial_by_id=state.get("initial_by_id"),
            angular_velocity=state.get("angular_velocity", 0.0),
        )
        if route is None:
            continue
        score = target.production * 20.0 - ships - route["travel_turns"] * 0.5 - route["risk"] * 4.0
        candidates.append((score, route["travel_turns"], target.id, [source.id, float(route["angle"]), ships]))
    if not candidates:
        return []
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [candidates[0][3]]


def plan_moves(state):
    opening = opening_first_capture(state)
    if opening:
        return opening
    proposals = []
    for source in state["mine"]:
        reserve = compute_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve))
        if surplus <= 0:
            continue
        for target in candidate_targets(state):
            rough = max(1, int(target.ships + max(2, target.production * 1.5)))
            rough_route = plan_route(
                source,
                target,
                rough,
                allow_offsets=True,
                initial_by_id=state.get("initial_by_id"),
                angular_velocity=state.get("angular_velocity", 0.0),
            )
            if rough_route is None:
                continue
            needed = ships_required(target, rough_route["travel_turns"])
            route = plan_route(
                source,
                target,
                needed,
                allow_offsets=True,
                initial_by_id=state.get("initial_by_id"),
                angular_velocity=state.get("angular_velocity", 0.0),
            )
            if route is None:
                continue
            route["ships"] = needed
            proposals.append((score_route(source, target, route, state), source, target, route))
    proposals.sort(key=lambda item: (-item[0], item[3]["risk"], item[3]["travel_turns"], item[2].id))
    moves = []
    source_spent = {}
    target_planned = {}
    for score, source, target, route in proposals:
        if score < -10:
            continue
        reserve = compute_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve - source_spent.get(source.id, 0)))
        remaining = int(math.ceil(route["ships"] - target_planned.get(target.id, 0)))
        ships = min(surplus, remaining)
        if ships <= 0:
            continue
        if ships < remaining:
            continue
        final_route = plan_route(source, target, ships, allow_offsets=True)
        if final_route is None:
            continue
        source_spent[source.id] = source_spent.get(source.id, 0) + ships
        target_planned[target.id] = target_planned.get(target.id, 0) + ships
        moves.append([source.id, float(final_route["angle"]), int(ships)])
    return moves


def agent(obs, config=None):
    try:
        return plan_moves(parse_state(obs))
    except Exception:
        return []

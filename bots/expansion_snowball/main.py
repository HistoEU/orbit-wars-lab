import math


BOARD_SIZE = 100.0
CENTER = 50.0
SUN_RADIUS = 10.0
SUN_SAFETY_MARGIN = 0.25
MAX_SPEED = 6.0
LAUNCH_CLEARANCE = 0.1

PRODUCTION_WEIGHT = 14.0
CLUSTER_WEIGHT = 4.0
FORWARD_BASE_WEIGHT = 2.5
DENIAL_WEIGHT = 5.0
SHIP_COST_WEIGHT = 1.0
TRAVEL_TURN_WEIGHT = 0.7
CONTEST_RISK_WEIGHT = 2.0
OVEREXTEND_WEIGHT = 3.0
SUN_RISK_PENALTY = 9999.0

MIN_LAUNCH = 1
MIN_SCORE = -20.0


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


class ScoredTarget:
    __slots__ = ("score", "ships_required", "angle", "travel_turns", "reason")

    def __init__(self, score, ships_required, angle, travel_turns, reason):
        self.score = float(score)
        self.ships_required = int(ships_required)
        self.angle = float(angle)
        self.travel_turns = int(travel_turns)
        self.reason = str(reason)


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


def parse_planet(raw, comet_ids=None):
    comet_ids = comet_ids or set()
    if isinstance(raw, (list, tuple)):
        planet_id = raw[0]
        return PlanetView(raw[0], raw[1], raw[2], raw[3], raw[4], raw[5], raw[6], int(planet_id) in comet_ids)
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
    fleets = [parse_fleet(f) for f in (read_field(obs, "fleets", []) or [])]
    players = list(read_field(obs, "players", []) or [])
    if players:
        player_count = len(players)
    else:
        owners = {p.owner for p in planets if p.owner >= 0}
        owners.update(f.owner for f in fleets if f.owner >= 0)
        player_count = max(2, len(owners))
    state = {
        "player": player,
        "step": as_int(read_field(obs, "step", 0), 0),
        "player_count": player_count,
        "planets": planets,
        "fleets": fleets,
        "mine": [p for p in planets if p.owner == player],
        "enemies": [p for p in planets if p.owner >= 0 and p.owner != player],
        "neutral": [p for p in planets if p.owner < 0],
        "targets": [p for p in planets if p.owner != player],
        "comet_planet_ids": comet_ids,
    }
    state["incoming_by_planet"] = compute_incoming_pressure(state)
    return state


def distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def point_distance(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


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


def segment_circle_distance(cx, cy, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return math.hypot(cx - x1, cy - y1)
    t = ((cx - x1) * dx + (cy - y1) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    return math.hypot(cx - (x1 + t * dx), cy - (y1 + t * dy))


def route_plan(source, target, ships):
    angle = math.atan2(target.y - source.y, target.x - source.x)
    sx, sy = launch_point(source, angle)
    tx, ty = target.x, target.y
    target_progress = segment_progress_to_circle(target.x, target.y, target.radius, sx, sy, tx, ty)
    sun_progress = segment_progress_to_circle(
        CENTER,
        CENTER,
        SUN_RADIUS + SUN_SAFETY_MARGIN,
        sx,
        sy,
        tx,
        ty,
    )
    if sun_progress is not None and (target_progress is None or sun_progress < target_progress):
        return None
    hit_distance = max(0.0, point_distance(sx, sy, tx, ty) - target.radius)
    travel_turns = max(1, int(math.ceil(hit_distance / fleet_speed(max(ships, 1)))))
    return angle, travel_turns


def fleet_threatens_planet(fleet, planet):
    speed = fleet_speed(fleet.ships)
    lookahead = max(15.0, speed * 30.0)
    ex = fleet.x + math.cos(fleet.angle) * lookahead
    ey = fleet.y + math.sin(fleet.angle) * lookahead
    progress = segment_progress_to_circle(planet.x, planet.y, planet.radius + 3.0, fleet.x, fleet.y, ex, ey)
    return progress is not None


def compute_incoming_pressure(state):
    incoming = {p.id: 0.0 for p in state["mine"]}
    for fleet in state["fleets"]:
        if fleet.owner == state["player"]:
            continue
        for planet in state["mine"]:
            if fleet_threatens_planet(fleet, planet):
                incoming[planet.id] += fleet.ships
    return incoming


def compute_reserve(source, state):
    incoming = state.get("incoming_by_planet", {}).get(source.id, 0.0)
    if state.get("step", 0) < 45 and incoming <= 0:
        base = max(5.0, float(source.production))
    else:
        base = max(5.0, source.production * 1.5)
    if state.get("step", 0) >= 300:
        base = max(base, source.production * 2.0)
    return max(base, incoming * 1.25)


def estimate_ships_required(source, target, state):
    rough_ships = max(1, int(target.ships + max(2.0, target.production * 1.5)))
    rough_route = route_plan(source, target, rough_ships)
    travel_turns = rough_route[1] if rough_route else 999
    margin = max(2.0, target.production * 1.5, target.ships * 0.08)
    growth = 0.0 if target.owner < 0 else max(0, target.production) * travel_turns
    return int(math.ceil(target.ships + growth + margin))


def phase_payback_limit(step):
    if step <= 45:
        return 45.0
    if step <= 260:
        return 35.0
    if step <= 420:
        return 20.0
    return 8.0


def cluster_value(target, state):
    value = 0.0
    for planet in state["targets"]:
        if planet.id == target.id:
            continue
        if point_distance(target.x, target.y, planet.x, planet.y) <= 22.0:
            value += min(2.0, max(0, planet.production) * 0.4)
    return value


def forward_base_value(source, target, state):
    if not state["enemies"]:
        return 0.0
    nearest_enemy_dist = min(distance(target, enemy) for enemy in state["enemies"])
    source_enemy_dist = min(distance(source, enemy) for enemy in state["enemies"])
    if nearest_enemy_dist >= source_enemy_dist:
        return 0.0
    return min(8.0, (source_enemy_dist - nearest_enemy_dist) / 10.0)


def contest_risk(target, state):
    if not state["enemies"]:
        return 0.0
    enemy_dist = min(point_distance(target.x, target.y, enemy.x, enemy.y) for enemy in state["enemies"])
    mine_dist = min(point_distance(target.x, target.y, mine.x, mine.y) for mine in state["mine"])
    if enemy_dist >= mine_dist:
        return 0.0
    return min(20.0, (mine_dist - enemy_dist) / 5.0)


def overextend_penalty(target, state):
    if state.get("player_count", 2) <= 2:
        return 0.0
    nearby_enemy_groups = sum(1 for enemy in state["enemies"] if point_distance(target.x, target.y, enemy.x, enemy.y) <= 30.0)
    return max(0, nearby_enemy_groups - 1) * 4.0


def score_target(source, target, state):
    ships_required = estimate_ships_required(source, target, state)
    route = route_plan(source, target, ships_required)
    if route is None:
        return ScoredTarget(-SUN_RISK_PENALTY, ships_required, 0.0, 999, "sun_blocked")
    angle, travel_turns = route
    production = max(0, target.production)
    payback = ships_required / max(1.0, float(production))
    payback_limit = phase_payback_limit(state.get("step", 0))
    payback_penalty = max(0.0, payback - payback_limit) * 2.0
    denial = DENIAL_WEIGHT if target.owner >= 0 else 0.0
    score = (
        production * PRODUCTION_WEIGHT
        + cluster_value(target, state) * CLUSTER_WEIGHT
        + forward_base_value(source, target, state) * FORWARD_BASE_WEIGHT
        + denial
        - ships_required * SHIP_COST_WEIGHT
        - travel_turns * TRAVEL_TURN_WEIGHT
        - contest_risk(target, state) * CONTEST_RISK_WEIGHT
        - overextend_penalty(target, state) * OVEREXTEND_WEIGHT
        - payback_penalty
    )
    return ScoredTarget(score, ships_required, angle, travel_turns, "scored")


def candidate_targets(state):
    step = state.get("step", 0)
    if step <= 45:
        neutrals = [p for p in state["neutral"] if not p.is_comet]
        return neutrals if neutrals else state["targets"]
    return [p for p in state["targets"] if not (p.is_comet and step < 120)]


def opening_first_capture(state):
    if state.get("step", 0) > 60 or len(state["mine"]) != 1 or not state["neutral"]:
        return []
    source = state["mine"][0]
    if state.get("incoming_by_planet", {}).get(source.id, 0.0) > 0:
        return []
    candidates = []
    for target in state["neutral"]:
        if target.is_comet:
            continue
        ships = int(math.floor(target.ships)) + 1
        if source.ships < ships + 1:
            continue
        route = route_plan(source, target, ships)
        if route is None:
            continue
        angle, turns = route
        score = target.production * 20.0 - ships - turns * 0.5
        candidates.append((score, turns, target.id, [source.id, float(angle), ships]))
    if not candidates:
        return []
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [candidates[0][3]]


def plan_moves(state):
    opening = opening_first_capture(state)
    if opening:
        return opening
    candidates = []
    targets = candidate_targets(state)
    for source in state["mine"]:
        reserve = compute_reserve(source, state)
        source_surplus = max(0.0, source.ships - reserve)
        if source_surplus < MIN_LAUNCH:
            continue
        for target in targets:
            scored = score_target(source, target, state)
            if scored.score <= MIN_SCORE:
                continue
            candidates.append((scored, source, target))

    candidates.sort(key=lambda item: (-item[0].score, item[0].travel_turns, item[2].id, item[1].id))
    source_spent = {}
    target_planned = {}
    target_need = {}
    moves = []
    for scored, source, target in candidates:
        reserve = compute_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve - source_spent.get(source.id, 0)))
        if surplus < MIN_LAUNCH:
            continue
        need = target_need.setdefault(target.id, scored.ships_required)
        remaining_need = int(math.ceil(need - target_planned.get(target.id, 0)))
        if remaining_need < MIN_LAUNCH:
            continue
        ships = min(surplus, remaining_need)
        if ships < MIN_LAUNCH:
            continue
        if ships < remaining_need:
            continue
        route = route_plan(source, target, ships)
        if route is None:
            continue
        angle, _turns = route
        source_spent[source.id] = source_spent.get(source.id, 0) + ships
        target_planned[target.id] = target_planned.get(target.id, 0) + ships
        moves.append([source.id, float(angle), int(ships)])
    return moves


def agent(obs, config=None):
    try:
        state = parse_state(obs)
        return plan_moves(state)
    except Exception:
        return []

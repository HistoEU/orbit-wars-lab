import math


BOARD_SIZE = 100.0
CENTER = 50.0
SUN_RADIUS = 10.0
SUN_SAFETY_MARGIN = 0.5
MAX_SPEED = 6.0
LAUNCH_CLEARANCE = 0.1
ANGLE_OFFSETS = [0.0, -0.06, 0.06, -0.12, 0.12, -0.20, 0.20]

ENEMY_PRODUCTION_WEIGHT = 12.0
ENEMY_SHIP_DENIAL_WEIGHT = 0.8
ENEMY_HOME_BONUS = 20.0
FORWARD_POSITION_WEIGHT = 2.0
LATE_SCORE_WEIGHT = 1.5
TRAVEL_WEIGHT = 1.0
COUNTER_RISK_WEIGHT = 2.5


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
    fleets = [parse_fleet(f) for f in (read_field(obs, "fleets", []) or [])]
    mine = [p for p in planets if p.owner == player]
    enemies = [p for p in planets if p.owner >= 0 and p.owner != player]
    owners = {p.owner for p in planets if p.owner >= 0}
    players = list(read_field(obs, "players", []) or [])
    state = {
        "player": player,
        "step": as_int(read_field(obs, "step", 0), 0),
        "player_count": len(players) if players else max(2, len(owners)),
        "planets": planets,
        "fleets": fleets,
        "mine": mine,
        "enemies": enemies,
        "neutral": [p for p in planets if p.owner < 0],
        "targets": [p for p in planets if p.owner != player],
    }
    my_total = sum(p.ships for p in mine) + sum(f.ships for f in fleets if f.owner == player)
    enemy_totals = []
    for owner in owners:
        if owner == player:
            continue
        total = sum(p.ships for p in planets if p.owner == owner) + sum(f.ships for f in fleets if f.owner == owner)
        enemy_totals.append(total)
    state["ship_delta"] = my_total - (max(enemy_totals) if enemy_totals else 0.0)
    state["incoming_by_planet"] = compute_incoming_pressure(state)
    return state


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


def plan_route(source, target, ships):
    base = math.atan2(target.y - source.y, target.x - source.x)
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
        route = {"angle": float(angle), "travel_turns": turns, "risk": abs(offset) * 10.0}
        if best is None or (route["risk"], route["travel_turns"]) < (best["risk"], best["travel_turns"]):
            best = route
    return best


def fleet_threatens_planet(fleet, planet):
    speed = fleet_speed(fleet.ships)
    lookahead = max(15.0, speed * 30.0)
    end_x = fleet.x + math.cos(fleet.angle) * lookahead
    end_y = fleet.y + math.sin(fleet.angle) * lookahead
    return segment_progress_to_circle(planet.x, planet.y, planet.radius + 3.0, fleet.x, fleet.y, end_x, end_y) is not None


def compute_incoming_pressure(state):
    incoming = {p.id: 0.0 for p in state.get("mine", [])}
    for fleet in state.get("fleets", []):
        if fleet.owner == state.get("player"):
            continue
        for planet in state.get("mine", []):
            if fleet_threatens_planet(fleet, planet):
                incoming[planet.id] += fleet.ships
    return incoming


def compute_reserve(source, state):
    incoming = state.get("incoming_by_planet", {}).get(source.id, 0.0)
    base = max(5.0, source.production * 1.5)
    if state.get("step", 0) < 45:
        base = max(5.0, source.production)
    return max(base, incoming * 1.25)


def capture_ships(target, travel_turns):
    margin = max(2.0, target.production * 1.5, target.ships * 0.10)
    growth = max(0, target.production) * travel_turns if target.owner >= 0 else 0.0
    return int(math.ceil(target.ships + growth + margin))


def pressure_budget_fraction(signals):
    step = int(signals.get("step", 0))
    ship_delta = float(signals.get("ship_delta", 0.0))
    if step < 90:
        return 0.15 if ship_delta < -20 else 0.08
    if step < 300:
        return 0.50 if ship_delta < -20 else 0.45
    return 0.60 if ship_delta < -20 else 0.25


def pressure_threshold(state):
    step = state.get("step", 0)
    if step < 90:
        return 35.0
    if step >= 300 and state.get("ship_delta", 0.0) < -20:
        return 5.0
    if state.get("ship_delta", 0.0) > 30:
        return 18.0
    return 12.0


def pressure_score(source, target, state):
    rough = max(1, int(target.ships + max(2, target.production * 1.5)))
    route = plan_route(source, target, rough)
    if route is None:
        return {"score": -9999.0, "purpose": "unsafe", "ships": 0, "route": None}
    ships = capture_ships(target, route["travel_turns"])
    route = plan_route(source, target, ships)
    if route is None:
        return {"score": -9999.0, "purpose": "unsafe", "ships": ships, "route": None}
    home_bonus = ENEMY_HOME_BONUS if target.production >= 5 and target.ships <= 20 else 0.0
    late_score = 0.0
    if state.get("step", 0) >= 300:
        late_score = max(0.0, -state.get("ship_delta", 0.0)) * 0.2
    counter_risk = max(0.0, ships - max(0.0, source.ships - compute_reserve(source, state)))
    score = (
        target.production * ENEMY_PRODUCTION_WEIGHT
        + target.ships * ENEMY_SHIP_DENIAL_WEIGHT
        + home_bonus
        + late_score * LATE_SCORE_WEIGHT
        - ships
        - route["travel_turns"] * TRAVEL_WEIGHT
        - route["risk"] * 3.0
        - counter_risk * COUNTER_RISK_WEIGHT
    )
    purpose = "capture"
    return {"score": score, "purpose": purpose, "ships": ships, "route": route}


def plan_pressure(state):
    proposals = []
    budget_fraction = pressure_budget_fraction(state)
    for source in state.get("mine", []):
        reserve = compute_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve))
        budget = int(math.floor(surplus * budget_fraction))
        if budget <= 0:
            continue
        for target in state.get("enemies", []):
            scored = pressure_score(source, target, state)
            if scored["score"] >= pressure_threshold(state) and scored["purpose"] in {"capture", "home_punish"}:
                proposals.append((scored["score"], source, target, scored, budget))
    proposals.sort(key=lambda item: (-item[0], item[3]["route"]["travel_turns"], item[2].id))
    moves = []
    source_spent = {}
    target_planned = {}
    for _score, source, target, scored, budget in proposals:
        reserve = compute_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve - source_spent.get(source.id, 0)))
        remaining_budget = budget - source_spent.get(source.id, 0)
        remaining_need = scored["ships"] - target_planned.get(target.id, 0)
        ships = min(surplus, remaining_budget, remaining_need)
        if ships <= 0 or ships < scored["ships"]:
            continue
        route = plan_route(source, target, ships)
        if route is None:
            continue
        source_spent[source.id] = source_spent.get(source.id, 0) + ships
        target_planned[target.id] = target_planned.get(target.id, 0) + ships
        moves.append([source.id, float(route["angle"]), int(ships)])
    return moves


def plan_expansion_fallback(state, reserved_sources=None):
    reserved_sources = reserved_sources or {}
    if state.get("step", 0) <= 45:
        targets = state.get("neutral", []) or state.get("targets", [])
    else:
        targets = list(state.get("neutral", [])) + list(state.get("enemies", []))
    proposals = []
    for source in state.get("mine", []):
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
    for _score, source, target, ships_needed, _route in proposals:
        reserve = compute_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve - source_spent.get(source.id, 0)))
        remaining = ships_needed - target_planned.get(target.id, 0)
        ships = min(surplus, remaining)
        if ships <= 0:
            continue
        if ships < remaining:
            continue
        route = plan_route(source, target, ships)
        if route is None:
            continue
        source_spent[source.id] = source_spent.get(source.id, 0) + ships
        target_planned[target.id] = target_planned.get(target.id, 0) + ships
        moves.append([source.id, float(route["angle"]), int(ships)])
    return moves


def opening_first_capture(state):
    if state.get("step", 0) > 60 or len(state.get("mine", [])) != 1 or not state.get("neutral", []):
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
        route = plan_route(source, target, ships)
        if route is None:
            continue
        score = target.production * 20.0 - ships - route["travel_turns"] * 0.5
        candidates.append((score, route["travel_turns"], target.id, [source.id, float(route["angle"]), ships]))
    if not candidates:
        return []
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [candidates[0][3]]


def plan_moves(state):
    opening = opening_first_capture(state)
    if opening:
        return opening
    pressure = plan_pressure(state)
    reserved = {}
    for source_id, _angle, ships in pressure:
        reserved[source_id] = reserved.get(source_id, 0) + ships
    return pressure + plan_expansion_fallback(state, reserved)


def agent(obs, config=None):
    try:
        return plan_moves(parse_state(obs))
    except Exception:
        return []

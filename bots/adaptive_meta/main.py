import math


BOARD_SIZE = 100.0
CENTER = 50.0
SUN_RADIUS = 10.0
SUN_SAFETY_MARGIN = 0.5
MAX_SPEED = 6.0
LAUNCH_CLEARANCE = 0.1
ANGLE_OFFSETS = [0.0, -0.06, 0.06, -0.12, 0.12, -0.20, 0.20]


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
    for group in list(read_field(obs, "comets", []) or []):
        planet_ids = [as_int(x) for x in (group.get("planet_ids", []) or [])]
        paths = group.get("paths", []) or []
        path_index = as_int(group.get("path_index", 0), 0)
        for index, planet_id in enumerate(planet_ids):
            if index >= len(paths):
                continue
            path = paths[index] or []
            meta[planet_id] = {
                "path": path,
                "path_index": path_index,
                "remaining_life": max(0, len(path) - path_index),
            }
    return meta


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


def compute_game_state(obs):
    player = as_int(read_field(obs, "player", 0), 0)
    comet_meta = parse_comets(obs)
    comet_ids = set(comet_meta)
    comet_ids.update(as_int(x) for x in (read_field(obs, "comet_planet_ids", []) or []))
    planets = [parse_planet(p, comet_ids) for p in (read_field(obs, "planets", []) or [])]
    fleets = [parse_fleet(f) for f in (read_field(obs, "fleets", []) or [])]
    players = list(read_field(obs, "players", []) or [])
    owners = {p.owner for p in planets if p.owner >= 0}
    owners.update(f.owner for f in fleets if f.owner >= 0)
    player_count = len(players) if players else max(2, len(owners))
    enemy_by_owner = {}
    for planet in planets:
        if planet.owner >= 0 and planet.owner != player:
            enemy_by_owner.setdefault(planet.owner, []).append(planet)
    state = {
        "player": player,
        "step": as_int(read_field(obs, "step", 0), 0),
        "player_count": player_count,
        "planets": planets,
        "fleets": fleets,
        "comet_meta": comet_meta,
        "my_planets": [p for p in planets if p.owner == player],
        "enemy_planets_by_owner": enemy_by_owner,
        "enemy_planets": [p for p in planets if p.owner >= 0 and p.owner != player],
        "neutral_planets": [p for p in planets if p.owner < 0],
        "comet_planets": [p for p in planets if p.is_comet],
    }
    state["incoming_by_planet"] = compute_incoming_pressure(state)
    return state


def phase_for_step(step):
    if step <= 90:
        return "early"
    if step <= 260:
        return "mid"
    if step <= 420:
        return "late"
    return "endgame"


def total_ships_for_owner(state, owner):
    return sum(p.ships for p in state["planets"] if p.owner == owner) + sum(f.ships for f in state["fleets"] if f.owner == owner)


def total_production(planets):
    return sum(max(0, p.production) for p in planets)


def compute_signals(state):
    player = state["player"]
    my_planets = state["my_planets"]
    enemy_groups = list(state["enemy_planets_by_owner"].values())
    best_enemy_planets = max((len(group) for group in enemy_groups), default=0)
    best_enemy_production = max((total_production(group) for group in enemy_groups), default=0)
    owners = set(state["enemy_planets_by_owner"])
    enemy_ship_totals = [total_ships_for_owner(state, owner) for owner in owners]
    my_ships = total_ships_for_owner(state, player)
    best_enemy_ships = max(enemy_ship_totals, default=0.0)
    incoming_threat = sum(state.get("incoming_by_planet", {}).values())
    return {
        "step": state["step"],
        "phase": phase_for_step(state["step"]),
        "player_count": state["player_count"],
        "production_delta": total_production(my_planets) - best_enemy_production,
        "ship_delta": my_ships - best_enemy_ships,
        "planet_delta": len(my_planets) - best_enemy_planets,
        "incoming_threat": incoming_threat,
        "good_comet_count": sum(1 for p in state["comet_planets"] if p.owner < 0),
        "is_ahead": my_ships > best_enemy_ships + 20,
    }


def choose_mode_budget(signals):
    phase = signals.get("phase", "early")
    ship_delta = float(signals.get("ship_delta", 0.0))
    player_count = int(signals.get("player_count", 2))
    if signals.get("incoming_threat", 0) > 0:
        return {"DEFEND": 55, "EXPAND": 25, "COMET": 5, "PRESSURE": 10, "ENDGAME_SCORE": 5}
    if player_count >= 4:
        if ship_delta > 30:
            return {"DEFEND": 40, "ENDGAME_SCORE": 20, "EXPAND": 25, "COMET": 5, "PRESSURE": 10}
        return {"EXPAND": 45, "DEFEND": 25, "COMET": 10, "PRESSURE": 15, "ENDGAME_SCORE": 5}
    if phase == "early":
        if ship_delta < -20:
            return {"EXPAND": 60, "DEFEND": 15, "COMET": 10, "PRESSURE": 10, "ENDGAME_SCORE": 5}
        return {"EXPAND": 65, "DEFEND": 20, "COMET": 10, "PRESSURE": 5, "ENDGAME_SCORE": 0}
    if phase == "mid":
        if ship_delta < -20:
            return {"PRESSURE": 35, "EXPAND": 30, "COMET": 20, "DEFEND": 15, "ENDGAME_SCORE": 0}
        return {"EXPAND": 30, "DEFEND": 25, "PRESSURE": 25, "COMET": 20, "ENDGAME_SCORE": 0}
    if phase == "late":
        if ship_delta < -20:
            return {"PRESSURE": 55, "ENDGAME_SCORE": 25, "COMET": 10, "DEFEND": 10, "EXPAND": 0}
        return {"DEFEND": 45, "ENDGAME_SCORE": 30, "PRESSURE": 15, "COMET": 5, "EXPAND": 5}
    if ship_delta < -20:
        return {"PRESSURE": 50, "ENDGAME_SCORE": 40, "DEFEND": 10, "EXPAND": 0, "COMET": 0}
    return {"DEFEND": 45, "ENDGAME_SCORE": 40, "PRESSURE": 15, "EXPAND": 0, "COMET": 0}


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
    values = [(-b - root) / (2.0 * a), (-b + root) / (2.0 * a)]
    valid = [t for t in values if 0.0 <= t <= 1.0]
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
        sun_progress = segment_progress_to_circle(CENTER, CENTER, SUN_RADIUS + SUN_SAFETY_MARGIN, sx, sy, far_x, far_y)
        if sun_progress is not None and sun_progress < target_progress:
            continue
        turns = max(1, int(math.ceil((target_progress * BOARD_SIZE * 2) / fleet_speed(ships))))
        route = {"angle": float(angle), "travel_turns": turns, "risk": abs(offset) * 10.0}
        if best is None or (route["risk"], route["travel_turns"]) < (best["risk"], best["travel_turns"]):
            best = route
    return best


def fleet_threatens_planet(fleet, planet):
    lookahead = max(15.0, fleet_speed(fleet.ships) * 30.0)
    end_x = fleet.x + math.cos(fleet.angle) * lookahead
    end_y = fleet.y + math.sin(fleet.angle) * lookahead
    return segment_progress_to_circle(planet.x, planet.y, planet.radius + 3.0, fleet.x, fleet.y, end_x, end_y) is not None


def compute_incoming_pressure(state):
    incoming = {p.id: 0.0 for p in state.get("my_planets", [])}
    for fleet in state.get("fleets", []):
        if fleet.owner == state.get("player"):
            continue
        for planet in state.get("my_planets", []):
            if fleet_threatens_planet(fleet, planet):
                incoming[planet.id] += fleet.ships
    return incoming


def compute_reserves(state, signals):
    reserves = {}
    for source in state["my_planets"]:
        incoming = state.get("incoming_by_planet", {}).get(source.id, 0.0)
        base = max(5.0, source.production if signals["phase"] == "early" else source.production * 1.75)
        if signals["phase"] in {"late", "endgame"} and signals.get("is_ahead"):
            base = max(base, source.production * 2.25)
        reserves[source.id] = max(base, incoming * 1.25)
    return reserves


def build_source_ledger(sources, reserves):
    ledger = {}
    for source in sources:
        reserve = float(reserves.get(source.id, 0.0))
        ledger[source.id] = {
            "ships": float(source.ships),
            "reserve": reserve,
            "spent": 0.0,
            "available": max(0.0, float(source.ships) - reserve),
        }
    return ledger


def capture_ships(target, travel_turns):
    margin = max(2.0, target.production * 1.5, target.ships * 0.08)
    growth = target.production * travel_turns if target.owner >= 0 else 0.0
    return int(math.ceil(target.ships + growth + margin))


def add_proposal(proposals, planner, source, target, ships, route, score, reason):
    proposals.append(
        {
            "planner": planner,
            "source_id": source.id,
            "target_id": target.id,
            "angle": float(route["angle"]),
            "ships": int(ships),
            "score": float(score),
            "risk": float(route.get("risk", 0.0)),
            "reason": reason,
        }
    )


def plan_expansion(state, signals):
    proposals = []
    targets = state["neutral_planets"]
    if not targets and signals["phase"] != "early":
        targets = state["enemy_planets"]
    for source in state["my_planets"]:
        for target in targets:
            rough = max(1, int(target.ships + max(2, target.production * 1.5)))
            route = plan_route(source, target, rough)
            if route is None:
                continue
            ships = capture_ships(target, route["travel_turns"])
            route = plan_route(source, target, ships)
            if route is None:
                continue
            score = target.production * 14.0 - ships - route["travel_turns"] * 0.7
            if score > -20:
                add_proposal(proposals, "EXPAND", source, target, ships, route, score, "payback_capture")
    return proposals


def plan_pressure(state, signals):
    proposals = []
    if signals["phase"] == "early" and signals["ship_delta"] >= -20:
        return proposals
    for source in state["my_planets"]:
        for target in state["enemy_planets"]:
            rough = max(1, int(target.ships + max(2, target.production * 1.5)))
            route = plan_route(source, target, rough)
            if route is None:
                continue
            ships = capture_ships(target, route["travel_turns"])
            route = plan_route(source, target, ships)
            if route is None:
                continue
            score = target.production * 12.0 + target.ships * 0.5 - ships - route["travel_turns"]
            if signals["phase"] in {"late", "endgame"} and signals["ship_delta"] < -20:
                score += 25.0
            if score > 5:
                add_proposal(proposals, "PRESSURE", source, target, ships, route, score, "weak_enemy_value")
    return proposals


def plan_comets(state, signals):
    proposals = []
    if not state["comet_planets"] or signals["phase"] == "endgame":
        return proposals
    for source in state["my_planets"]:
        for target in state["comet_planets"]:
            if target.owner == state["player"]:
                continue
            meta = state["comet_meta"].get(target.id, {})
            remaining = meta.get("remaining_life", 0)
            if remaining < 12:
                continue
            rough = max(1, int(target.ships + max(2, target.production * 1.5)))
            route = plan_route(source, target, rough)
            if route is None or remaining - route["travel_turns"] < 8:
                continue
            ships = capture_ships(target, route["travel_turns"])
            score = (remaining - route["travel_turns"]) * target.production * 1.5 - ships - route["travel_turns"]
            if score > 0:
                add_proposal(proposals, "COMET", source, target, ships, route, score, "good_comet")
    return proposals


def plan_endgame_score(state, signals):
    if signals["phase"] not in {"late", "endgame"}:
        return []
    proposals = []
    for source in state["my_planets"]:
        for target in state["enemy_planets"]:
            rough = max(1, int(target.ships + 2))
            route = plan_route(source, target, rough)
            if route is None or route["travel_turns"] > 35:
                continue
            ships = capture_ships(target, route["travel_turns"])
            score = target.ships + target.production * 5 - ships - route["travel_turns"]
            if score > 0:
                add_proposal(proposals, "ENDGAME_SCORE", source, target, ships, route, score, "score_swing")
    return proposals


def merge_proposals(proposals, ledger, budgets):
    priority = {"DEFEND": 0, "ENDGAME_SCORE": 1, "PRESSURE": 2, "COMET": 3, "EXPAND": 4}
    proposals = sorted(proposals, key=lambda p: (priority.get(p["planner"], 9), -p.get("score", 0.0), p.get("risk", 0.0)))
    budget_spent = {name: 0.0 for name in budgets}
    target_planned = {}
    moves = []
    for proposal in proposals:
        source_id = int(proposal["source_id"])
        target_id = int(proposal.get("target_id", -1))
        ships = int(proposal["ships"])
        planner = proposal.get("planner", "EXPAND")
        source = ledger.get(source_id)
        if source is None or ships <= 0:
            continue
        if source["spent"] + ships > source["available"]:
            continue
        if budget_spent.get(planner, 0.0) + ships > float(budgets.get(planner, 0.0)):
            continue
        if target_planned.get(target_id, 0) >= ships:
            continue
        source["spent"] += ships
        budget_spent[planner] = budget_spent.get(planner, 0.0) + ships
        target_planned[target_id] = target_planned.get(target_id, 0) + ships
        moves.append([source_id, float(proposal["angle"]), ships])
    return moves


def scale_budgets_to_ships(budgets, ledger):
    total_available = sum(source["available"] for source in ledger.values())
    return {name: max(0.0, total_available * value / 100.0) for name, value in budgets.items()}


def plan_moves(state):
    signals = compute_signals(state)
    reserves = compute_reserves(state, signals)
    ledger = build_source_ledger(state["my_planets"], reserves)
    budgets = scale_budgets_to_ships(choose_mode_budget(signals), ledger)
    proposals = []
    proposals.extend(plan_expansion(state, signals))
    proposals.extend(plan_comets(state, signals))
    proposals.extend(plan_pressure(state, signals))
    proposals.extend(plan_endgame_score(state, signals))
    return merge_proposals(proposals, ledger, budgets)


def agent(obs, config=None):
    try:
        return plan_moves(compute_game_state(obs))
    except Exception:
        return []

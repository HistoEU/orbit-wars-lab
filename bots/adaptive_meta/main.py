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
        if signals.get("production_delta", 0) < -8 or signals.get("planet_delta", 0) < -1:
            return {"EXPAND": 55, "PRESSURE": 25, "COMET": 10, "DEFEND": 10, "ENDGAME_SCORE": 0}
        if ship_delta < -40:
            return {"EXPAND": 40, "PRESSURE": 30, "COMET": 15, "DEFEND": 15, "ENDGAME_SCORE": 0}
        return {"EXPAND": 45, "PRESSURE": 35, "DEFEND": 10, "COMET": 10, "ENDGAME_SCORE": 0}
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
    targets = list(state["neutral_planets"])
    if signals["phase"] != "early":
        targets.extend(state["enemy_planets"])
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


def economy_compute_reserve(source, state):
    incoming = state.get("incoming_by_planet", {}).get(source.id, 0.0)
    if state.get("step", 0) < 45 and incoming <= 0:
        base = max(5.0, float(source.production))
    else:
        base = max(5.0, source.production * 1.5)
    if state.get("step", 0) >= 300:
        base = max(base, source.production * 2.0)
    return max(base, incoming * 1.25)


def economy_phase_payback_limit(step):
    if step <= 45:
        return 45.0
    if step <= 260:
        return 35.0
    if step <= 420:
        return 20.0
    return 8.0


def economy_targets(state):
    step = state.get("step", 0)
    if step <= 45:
        neutrals = [p for p in state["neutral_planets"] if not p.is_comet]
        return neutrals if neutrals else [p for p in state["planets"] if p.owner != state["player"]]
    return [
        p
        for p in state["planets"]
        if p.owner != state["player"] and not (p.is_comet and step < 120)
    ]


def economy_cluster_value(target, state):
    value = 0.0
    for planet in state["neutral_planets"] + state["enemy_planets"]:
        if planet.id == target.id:
            continue
        if dist_xy(target.x, target.y, planet.x, planet.y) <= 22.0:
            value += min(2.0, max(0, planet.production) * 0.4)
    return value


def economy_forward_base_value(source, target, state):
    if not state["enemy_planets"]:
        return 0.0
    nearest_enemy_dist = min(distance(target, enemy) for enemy in state["enemy_planets"])
    source_enemy_dist = min(distance(source, enemy) for enemy in state["enemy_planets"])
    if nearest_enemy_dist >= source_enemy_dist:
        return 0.0
    return min(8.0, (source_enemy_dist - nearest_enemy_dist) / 10.0)


def economy_contest_risk(target, state):
    if not state["enemy_planets"]:
        return 0.0
    enemy_dist = min(dist_xy(target.x, target.y, enemy.x, enemy.y) for enemy in state["enemy_planets"])
    mine_dist = min(dist_xy(target.x, target.y, mine.x, mine.y) for mine in state["my_planets"])
    if enemy_dist >= mine_dist:
        return 0.0
    return min(20.0, (mine_dist - enemy_dist) / 5.0)


def economy_overextend_penalty(target, state):
    if state.get("player_count", 2) <= 2:
        return 0.0
    nearby_enemy_groups = sum(
        1 for enemy in state["enemy_planets"] if dist_xy(target.x, target.y, enemy.x, enemy.y) <= 30.0
    )
    return max(0, nearby_enemy_groups - 1) * 4.0


def economy_score_target(source, target, state):
    rough = max(1, int(target.ships + max(2.0, target.production * 1.5)))
    rough_route = plan_route(source, target, rough)
    if rough_route is None:
        return None
    ships_required = capture_ships(target, rough_route["travel_turns"])
    route = plan_route(source, target, ships_required)
    if route is None:
        return None
    production = max(0, target.production)
    payback = ships_required / max(1.0, float(production))
    payback_penalty = max(0.0, payback - economy_phase_payback_limit(state.get("step", 0))) * 2.0
    denial = 5.0 if target.owner >= 0 else 0.0
    score = (
        production * 14.0
        + economy_cluster_value(target, state) * 4.0
        + economy_forward_base_value(source, target, state) * 2.5
        + denial
        - ships_required
        - route["travel_turns"] * 0.7
        - economy_contest_risk(target, state) * 2.0
        - economy_overextend_penalty(target, state) * 3.0
        - payback_penalty
    )
    return {"score": score, "ships_required": ships_required, "route": route}


def economy_plan_moves(state):
    opening = opening_first_capture(state)
    if opening:
        return opening
    candidates = []
    for source in state["my_planets"]:
        reserve = economy_compute_reserve(source, state)
        if source.ships - reserve < 1:
            continue
        for target in economy_targets(state):
            scored = economy_score_target(source, target, state)
            if scored is None or scored["score"] <= -20.0:
                continue
            candidates.append((scored, source, target))
    candidates.sort(key=lambda item: (-item[0]["score"], item[0]["route"]["travel_turns"], item[2].id, item[1].id))

    source_spent = {}
    target_planned = {}
    target_need = {}
    moves = []
    for scored, source, target in candidates:
        reserve = economy_compute_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve - source_spent.get(source.id, 0)))
        if surplus < 1:
            continue
        need = target_need.setdefault(target.id, scored["ships_required"])
        remaining_need = int(math.ceil(need - target_planned.get(target.id, 0)))
        if remaining_need < 1:
            continue
        ships = min(surplus, remaining_need)
        if ships < remaining_need:
            continue
        route = plan_route(source, target, ships)
        if route is None:
            continue
        source_spent[source.id] = source_spent.get(source.id, 0) + ships
        target_planned[target.id] = target_planned.get(target.id, 0) + ships
        moves.append([source.id, float(route["angle"]), int(ships)])
    return moves


def pressure_champion_reserve(source, state):
    incoming = state.get("incoming_by_planet", {}).get(source.id, 0.0)
    base = max(5.0, source.production * 1.5)
    if state.get("step", 0) < 45:
        base = max(5.0, source.production)
    return max(base, incoming * 1.25)


def pressure_champion_budget_fraction(state):
    step = int(state.get("step", 0))
    ship_delta = float(compute_signals(state).get("ship_delta", 0.0))
    if step < 90:
        return 0.15 if ship_delta < -20 else 0.08
    if step < 300:
        return 0.50 if ship_delta < -20 else 0.45
    return 0.60 if ship_delta < -20 else 0.25


def pressure_champion_threshold(state):
    step = state.get("step", 0)
    ship_delta = float(compute_signals(state).get("ship_delta", 0.0))
    if step < 90:
        return 35.0
    if step >= 300 and ship_delta < -20:
        return 5.0
    if ship_delta > 30:
        return 18.0
    return 12.0


def pressure_champion_score(source, target, state):
    rough = max(1, int(target.ships + max(2, target.production * 1.5)))
    route = plan_route(source, target, rough)
    if route is None:
        return {"score": -9999.0, "ships": 0, "route": None}
    ships = capture_ships(target, route["travel_turns"])
    route = plan_route(source, target, ships)
    if route is None:
        return {"score": -9999.0, "ships": ships, "route": None}
    signals = compute_signals(state)
    home_bonus = 20.0 if target.production >= 5 and target.ships <= 20 else 0.0
    late_score = max(0.0, -signals.get("ship_delta", 0.0)) * 0.2 if state.get("step", 0) >= 300 else 0.0
    counter_risk = max(0.0, ships - max(0.0, source.ships - pressure_champion_reserve(source, state)))
    score = (
        target.production * 12.0
        + target.ships * 0.8
        + home_bonus
        + late_score * 1.5
        - ships
        - route["travel_turns"]
        - route["risk"] * 3.0
        - counter_risk * 2.5
    )
    return {"score": score, "ships": ships, "route": route}


def pressure_champion_attacks(state):
    proposals = []
    budget_fraction = pressure_champion_budget_fraction(state)
    for source in state.get("my_planets", []):
        reserve = pressure_champion_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve))
        budget = int(math.floor(surplus * budget_fraction))
        if budget <= 0:
            continue
        for target in state.get("enemy_planets", []):
            scored = pressure_champion_score(source, target, state)
            if scored["score"] >= pressure_champion_threshold(state):
                proposals.append((scored["score"], source, target, scored, budget))
    proposals.sort(key=lambda item: (-item[0], item[3]["route"]["travel_turns"], item[2].id))
    moves = []
    source_spent = {}
    target_planned = {}
    for _score, source, target, scored, budget in proposals:
        reserve = pressure_champion_reserve(source, state)
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


def pressure_champion_expansion(state, reserved_sources=None):
    reserved_sources = reserved_sources or {}
    if state.get("step", 0) <= 45:
        targets = list(state.get("neutral_planets", [])) or [p for p in state["planets"] if p.owner != state["player"]]
    else:
        targets = list(state.get("neutral_planets", [])) + list(state.get("enemy_planets", []))
    proposals = []
    for source in state.get("my_planets", []):
        reserve = pressure_champion_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve - reserved_sources.get(source.id, 0)))
        if surplus <= 0:
            continue
        for target in targets:
            if target.is_comet:
                continue
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
        reserve = pressure_champion_reserve(source, state)
        surplus = int(math.floor(source.ships - reserve - source_spent.get(source.id, 0)))
        remaining = ships_needed - target_planned.get(target.id, 0)
        ships = min(surplus, remaining)
        if ships <= 0 or ships < remaining:
            continue
        route = plan_route(source, target, ships)
        if route is None:
            continue
        source_spent[source.id] = source_spent.get(source.id, 0) + ships
        target_planned[target.id] = target_planned.get(target.id, 0) + ships
        moves.append([source.id, float(route["angle"]), int(ships)])
    return moves


def pressure_champion_moves(state):
    opening = opening_first_capture(state)
    if opening:
        return opening
    pressure = pressure_champion_attacks(state)
    reserved = {}
    for source_id, _angle, ships in pressure:
        reserved[source_id] = reserved.get(source_id, 0) + ships
    return pressure + pressure_champion_expansion(state, reserved)


def economy_guard_moves(state, signals, ledger, proposals):
    if signals["phase"] not in {"early", "mid"}:
        return []
    if signals.get("player_count", 2) > 2 or signals.get("incoming_threat", 0) > 0:
        return []
    neutral_ids = {target.id for target in state["neutral_planets"] if not target.is_comet}
    expansion_proposals = [
        proposal
        for proposal in proposals
        if proposal.get("planner") == "EXPAND" and int(proposal.get("target_id", -1)) in neutral_ids
    ]
    if not expansion_proposals:
        return []
    guard_ledger = {source_id: dict(source) for source_id, source in ledger.items()}
    guard_budget = {"EXPAND": sum(source["available"] for source in guard_ledger.values())}
    return merge_proposals(expansion_proposals, guard_ledger, guard_budget)


def opening_first_capture(state):
    if state.get("step", 0) > 60 or len(state["my_planets"]) != 1 or not state["neutral_planets"]:
        return []
    source = state["my_planets"][0]
    if state.get("incoming_by_planet", {}).get(source.id, 0.0) > 0:
        return []
    candidates = []
    for target in state["neutral_planets"]:
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
    signals = compute_signals(state)
    if signals.get("player_count", 2) <= 2:
        champion = pressure_champion_moves(state)
        if champion:
            return champion
    economy_moves = economy_plan_moves(state)
    if (
        economy_moves
        and signals["phase"] == "early"
        and signals.get("player_count", 2) <= 2
        and signals.get("incoming_threat", 0) <= 0
    ):
        return economy_moves
    reserves = compute_reserves(state, signals)
    ledger = build_source_ledger(state["my_planets"], reserves)
    budgets = scale_budgets_to_ships(choose_mode_budget(signals), ledger)
    proposals = []
    proposals.extend(plan_expansion(state, signals))
    proposals.extend(plan_comets(state, signals))
    proposals.extend(plan_pressure(state, signals))
    proposals.extend(plan_endgame_score(state, signals))
    guarded = economy_guard_moves(state, signals, ledger, proposals)
    if guarded:
        return guarded
    return merge_proposals(proposals, ledger, budgets)


def agent(obs, config=None):
    try:
        return plan_moves(compute_game_state(obs))
    except Exception:
        return []

# Safe Geometry Pathfinder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox syntax for tracking.

**Goal:** Build a one-file Orbit Wars bot that wins or loses without wasting ships on bad routes, sun collisions, impossible intercepts, or accidental target misses.

**Architecture:** The bot is a route-first planner. It scores targets only after a safe route candidate exists. The geometry helpers are pure functions so they can be copied into every other bot variant.

**Tech Stack:** Python Kaggle agent in `bots/safe_geometry/main.py`, `pytest` for deterministic geometry tests, `tools/run_pvp.py` for PvP validation, viewer analytics for flaw inspection.

---

## File Structure

- Create: `bots/safe_geometry/main.py`
- Create: `tests/test_safe_geometry.py`
- Use existing: `tools/run_pvp.py`
- Use existing: `tools/analyze_run.py`
- Use existing: `viewer/index.html`
- Later copy stable helper functions into the other one-file bot submissions.

## Page 1: Strategic Identity And Full Mechanics Coverage

This bot exists to eliminate the dumbest expensive mistakes. In Orbit Wars, a bot can have a good target and still lose because the fleet dies before arrival, arrives too late, hits the wrong object, or crosses the sun. The safe geometry bot should become the trusted movement engine for the whole lab.

The bot should account for:

- source planet position,
- source radius and launch point,
- target current position,
- target radius,
- target movement if orbiting,
- fleet speed as a function of ship count,
- estimated travel time,
- sun center and sun radius,
- target collision progress,
- sun collision progress,
- unintended planet collision progress,
- board boundary risk,
- minimum launch size,
- source reserve,
- target ownership at launch time,
- whether a route needs direct aim or offset aim.

The strategic rule is simple: no route, no launch. Target scoring cannot override route safety. The bot should be allowed to be too conservative in version one because conservative pathing is easier to improve than reckless pathing.

Classify every route candidate internally:

```text
direct_safe
predicted_safe
offset_safe
sun_blocked
planet_blocked
out_of_bounds
too_slow
too_expensive
source_under_reserved
```

Only `direct_safe`, `predicted_safe`, and `offset_safe` can become moves.

## Page 2: Geometry Model, Collision Order, And Build Ideas

Implement pure helpers first:

```python
def dist(a, b): ...
def angle_to(a, b): ...
def clamp(value, low, high): ...
def closest_point_on_segment(a, b, p): ...
def segment_circle_distance(a, b, center): ...
def ray_circle_progress(a, b, center, radius): ...
def segment_hits_circle_before_target(a, b, center, radius, target_progress): ...
```

The most important detail is collision order. A fleet path may intersect the sun mathematically, but if it hits the target before reaching the sun, the launch is not a sun death. Compute progress along the segment:

```text
source = 0.0
target_collision = value between 0.0 and 1.0
sun_collision = value between 0.0 and 1.0 or none
unsafe if sun_collision exists and sun_collision < target_collision
```

Build idea: route quality should not be boolean forever. Version one can reject unsafe routes, but version two should score risk:

```text
risk = sun_margin_penalty + unintended_collision_penalty + long_travel_penalty + target_motion_penalty
```

Offset aiming:

```python
ANGLE_OFFSETS = [0.0, -0.06, 0.06, -0.12, 0.12, -0.20, 0.20, -0.30, 0.30]
```

Each offset creates an aim point around the target. The route planner chooses the safe route with the lowest combined travel and offset penalty.

Build idea for accidental collisions:

- First version rejects routes where another planet is hit before the intended target.
- Later version may allow "capture useful blocker" if the blocker is neutral, cheap, and valuable.
- Do not add blocker exploitation until the base route planner has clean test coverage.

## Page 3: Moving Targets, Route Plans, Reserve, And Action Generation

Moving targets require prediction. The planner should use a two-pass solve:

1. Aim at current target position.
2. Estimate travel time.
3. Predict target position at arrival.
4. Recompute angle.
5. Estimate travel time again.
6. Check collision order.
7. Check offset alternatives.

Prediction model:

```text
future_angle = current_orbit_angle + angular_velocity * travel_turns
future_x = center_x + orbit_radius * cos(future_angle)
future_y = center_y + orbit_radius * sin(future_angle)
```

If exact orbit metadata is unavailable, infer movement from current path fields when possible. If there is not enough information, treat target as static and apply a `target_motion_penalty`.

Route plan object:

```python
route = {
    "source_id": source_id,
    "target_id": target_id,
    "angle": angle,
    "ships": ships,
    "travel_turns": travel_turns,
    "risk": risk,
    "reason": "offset_safe",
}
```

Source reserve still matters:

```text
surplus = source_ships - reserve - already_spent
if surplus < ships_required:
    no launch
```

The final action generation should be boring:

```python
return [[route["source_id"], route["angle"], route["ships"]], ...]
```

No route metadata should be returned to Kaggle unless the environment explicitly supports it.

## Page 4: Bite-Sized Implementation Tasks

### Task 1: Geometry Primitives

**Files:**

- Create: `bots/safe_geometry/main.py`
- Create: `tests/test_safe_geometry.py`

- [ ] **Step 1: Write tests for distance and angle**

```python
def test_angle_to_right_is_zero():
    assert abs(angle_to((0, 0), (10, 0))) < 1e-9
```

- [ ] **Step 2: Implement `dist` and `angle_to`**
- [ ] **Step 3: Run `pytest tests/test_safe_geometry.py -v`**

### Task 2: Sun Collision Order

- [ ] **Step 1: Test a segment through the sun before target is unsafe**
- [ ] **Step 2: Test a segment that reaches target before sun is safe**
- [ ] **Step 3: Test a tangent-like near miss is safe**
- [ ] **Step 4: Implement `ray_circle_progress` and route rejection**

### Task 3: Offset Route Planner

- [ ] **Step 1: Create a target where direct route is blocked but offset is safe**
- [ ] **Step 2: Implement candidate angle offsets**
- [ ] **Step 3: Choose best safe candidate by risk then travel time**
- [ ] **Step 4: Return `None` when all candidates fail**

### Task 4: Moving Target Prediction

- [ ] **Step 1: Test orbiting target future position changes with turn count**
- [ ] **Step 2: Implement two-pass travel estimate**
- [ ] **Step 3: Assert route angle changes for moving target**

### Task 5: Bot Integration

- [ ] **Step 1: Parse state**
- [ ] **Step 2: Build safe routes to neutral and enemy targets**
- [ ] **Step 3: Score only routes, not raw targets**
- [ ] **Step 4: Generate legal moves**
- [ ] **Step 5: Run PvP smoke**

```powershell
.venv-ow\Scripts\python tools\run_pvp.py --agents bots/safe_geometry/main.py bots/starter/main.py --seeds 1 2 3 4 5 6 7 8 9 10 --viewer-replays --focus-agent bots/safe_geometry/main.py
```

## Page 5: Analytics, Tuning, Viewer Review, And Goals

Primary metrics:

- `bad_launch_sun_lane`,
- `sun_death`,
- `fleet_disappeared_without_capture`,
- issue severity P0/P1,
- win rate after safety improvements,
- expansion speed lost because of conservatism.

Viewer review checklist:

- Do fleet arrows avoid the sun?
- Are offset routes still hitting the target?
- Are any fleets disappearing before capture?
- Is the bot skipping too many valuable targets?
- Does a loss come from geometry, slow expansion, or no pressure?
- Are moving planets being aimed at current position or future position?

Tuning knobs:

```text
SUN_RADIUS_MARGIN: 0.0, 0.5, 1.0
ANGLE_OFFSETS: small, medium, large
MAX_ROUTE_RISK: 0, 5, 15
MOTION_PENALTY: 0, 5, 12
UNINTENDED_COLLISION_POLICY: reject, penalize
```

High-end build ideas:

- Add multi-hop route staging through safe owned planets.
- Add predicted ownership at arrival so the bot does not fly into changed targets blindly.
- Add comet intercept prediction from path metadata.
- Add "route confidence" and make adaptive meta spend fewer ships on low-confidence routes.
- Add a viewer overlay export later showing intended route classifications.

## Edge Cases And Detection Rules

Account for these edge cases explicitly:

- **Target close to the sun edge:** direct path may be mathematically valid but too risky with floating-point error. Add a small sun margin.
- **Source close to the sun edge:** launch point matters. Do not start the segment at planet center if ships spawn from surface.
- **Very large fleet speed:** fast fleets change travel time and moving-target intercepts. Test small and large ship counts.
- **Very small fleet speed:** slow fleets can miss orbiting targets. Penalize low-confidence moving intercepts.
- **Target behind another neutral:** reject accidental collision first; exploitation can come only after clean baseline.
- **Target already owned by us:** do not launch unless reinforcing under threat.
- **Route near board edge:** reject if predicted movement leaves the legal board before arrival.
- **Multiple safe offsets:** choose the one with shortest travel and smallest offset from target center.

Detection rules for replay analysis:

```text
bad_launch_sun_lane:
  route segment intersects sun before target

sun_death_suspect:
  fleet disappears near sun
  no planet capture occurred within expected arrival window

missed_target_suspect:
  fleet passes near intended target
  target remains uncaptured
  no enemy interaction explains disappearance

overconservative_route:
  safe target exists
  source has surplus
  no launch for 20 steps
```

The safe geometry bot should produce very few P1 movement issues. If it loses because it refuses to expand, that is acceptable data. If it loses because ships vanish, the route planner is not ready to copy into other bots.

## Codex Execution Loop

Use this loop:

1. Add one geometry test with fixed coordinates.
2. Run `pytest tests/test_safe_geometry.py -v`.
3. Implement the pure helper.
4. Add one route-planner test using the helper.
5. Run the focused tests again.
6. Add a five-seed PvP smoke.
7. Open any replay with `sun_death` or `fleet_disappeared_without_capture`.
8. Commit only after the issue count moves in the right direction.

Suggested commit sequence:

```text
feat: add safe geometry primitives
feat: add sun collision order checks
feat: add offset route planner
feat: add moving target route prediction
feat: integrate safe geometry bot planner
```

## Implementation Notes For The First Build

The route planner should be strict but explainable. If a launch is skipped, there should be a local reason: sun blocked, planet blocked, too slow, too expensive, or source under reserve. Do not silently return no move from the middle of the planner. Silent skips make tuning miserable.

Use simple coordinate fixtures in tests rather than full game observations for geometry math. A geometry bug should fail in a five-line test, not only after running a tournament. Then add a small number of integration tests that parse real-looking observations and call the agent.

Treat floating point carefully. Add a small safety margin around the sun so near misses are not accepted by accident. Keep this margin tunable:

```python
SUN_SAFETY_MARGIN = 0.5
```

For moving targets, do not chase perfect physics on day one. Two-pass prediction is enough to expose whether moving-target awareness improves results. If moving prediction makes routes worse, add a confidence penalty and fall back to static aiming for low-value targets.

When merging into other bots, copy the exact same helper functions and tests. Do not rewrite the math by memory. The purpose of this variant is to create one trusted route system, not five similar systems with five different bugs.

Loss buckets for review:

- no route available but human can see safe route,
- offset route chosen but misses target,
- direct route accepted but sun death occurs,
- moving target prediction sends fleet behind target,
- source reserve blocks too many useful launches,
- route planner is clean but strategy is too passive.

Each bucket has a different fix. Do not solve passivity by weakening sun safety until movement issues are actually clean.

## Success Review Matrix

Review safe geometry with this matrix after every batch:

```text
If sun deaths fall and win rate falls:
  route safety improved, strategy needs stronger target selection.

If sun deaths stay high:
  collision order or launch-point math is wrong.

If vanished fleets rise:
  unintended planet collision or moving-target prediction is wrong.

If no launches happen for long stretches:
  route thresholds are too strict or reserve is too high.

If offset launches miss:
  offset aim point is not aligned with actual collision mechanics.

If moving targets are missed:
  two-pass prediction needs better travel-time estimate or confidence penalty.
```

This matrix keeps tuning disciplined. It prevents the common mistake of weakening safety because the bot looks passive when the real fix is better route candidates.

## Detailed Goals At The Bottom

- Reduce `sun_death` by at least 80% compared with unsafe baselines.
- Reduce `bad_launch_sun_lane` by at least 80%.
- Complete 200 PvP games with zero agent crashes.
- Beat `bots/random_hold/main.py` consistently.
- Stay close enough to starter win rate that safety can be merged into stronger bots.
- Produce route helpers clean enough to copy into every other one-file bot.

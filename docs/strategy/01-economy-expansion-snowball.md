# Economy Expansion Snowball Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox syntax for tracking.

**Goal:** Build a one-file Orbit Wars bot that wins by taking the best production earlier than opponents, converting that production into a ship lead, and avoiding wasteful over-expansion.

**Architecture:** The bot is a deterministic planner with five layers: observation parsing, route safety, target valuation, reserve calculation, and launch assignment. It must be readable enough to tune quickly after replay analysis.

**Tech Stack:** Python Kaggle agent in `bots/expansion_snowball/main.py`, tested with `pytest`, evaluated with `tools/run_pvp.py`, reviewed in the local viewer.

---

## File Structure

- Create: `bots/expansion_snowball/main.py`
- Create: `tests/test_expansion_snowball.py`
- Use existing: `tools/run_pvp.py`
- Use existing: `tools/analyze_run.py`
- Use existing: `viewer/index.html`
- Do not import from `src/orbitlab` in the final bot file. Kaggle submissions must work as one file.

## Page 1: Strategic Identity And Mechanics Coverage

This bot should be the internal baseline champion. It is not meant to be clever in one narrow situation. It is meant to become strong across normal seeds by doing the core game better than starter: capture valuable planets, keep enough reserve, avoid bad launches, and scale production into ships.

The strategy has four phases:

- **Opening, steps 0-45:** capture the best safe neutral. Prefer short payback and low risk. Home may run a lower reserve because early attack pressure is usually limited.
- **Expansion, steps 46-120:** chain captures from newly owned planets. Avoid launching all ships from home if a forward planet can capture a nearby neutral.
- **Conversion, steps 121-300:** turn production lead into map control. Capture clusters, defend high-production planets, and start attacking exposed enemy production.
- **Scoring, steps 301-end:** reduce long-payback expansion. Value immediate ship swing, enemy planet denial, and safe final pressure.

The bot must account for these variables every turn:

- planet owner,
- planet ships,
- planet production,
- distance from source,
- expected travel time,
- target payback,
- source reserve,
- incoming enemy pressure,
- planned friendly fleets already going to target,
- whether the target is neutral, enemy, comet, or owned,
- sun route risk,
- whether the target is part of a production cluster,
- whether capture creates a forward launch pad,
- whether the game is 2P or 4P.

The core mental model is payback. A production planet is not valuable because it has a large production number in isolation. It is valuable if it repays the ships spent before the game state changes. A production 5 planet with 50 ships can be bad if it is too far away. A production 2 planet with 9 ships can be excellent if it becomes a safe forward base early.

## Page 2: Target Valuation, Opening Book, And Build Ideas

Build a target scoring function that returns a transparent numeric score plus a reason. The reason does not need to be submitted to Kaggle, but it should exist in local tests while tuning.

Suggested scoring:

```text
score =
  production * production_weight
  + cluster_value
  + forward_base_value
  + denial_value
  - capture_cost * ship_cost_weight
  - travel_turns * travel_weight
  - sun_risk_penalty
  - contest_risk_penalty
  - overextension_penalty
```

Starting weights:

```python
PRODUCTION_WEIGHT = 14.0
CLUSTER_WEIGHT = 4.0
FORWARD_BASE_WEIGHT = 2.5
DENIAL_WEIGHT = 5.0
SHIP_COST_WEIGHT = 1.0
TRAVEL_TURN_WEIGHT = 0.7
CONTEST_RISK_WEIGHT = 2.0
OVEREXTEND_WEIGHT = 3.0
SUN_RISK_PENALTY = 9999.0
```

Opening book build ideas:

- For the first move, score only safe neutral planets.
- If two targets have similar score, choose the one with lower travel time.
- If the best target crosses the sun, skip it completely.
- If the best target needs more than 70% of home ships, choose the second-best target unless payback is excellent.
- If no target clears the score threshold, hold for one turn rather than launching a useless fleet.

Payback rules:

```text
opening payback limit: 45 turns
midgame payback limit: 35 turns
late payback limit: 20 turns
endgame payback limit: only immediate score swing
```

Capture cost estimate:

```text
neutral_cost = neutral_ships + margin
enemy_cost = enemy_ships + enemy_production * travel_turns + margin
margin = max(2, target_production * 1.5, target_ships * 0.08)
```

If neutral planets do not produce while neutral in the actual environment, keep neutral cost simple. If they do produce, add `neutral_production * travel_turns`.

Cluster value build idea:

- Count nearby planets within a radius of 18-24 board units.
- Reward clusters where at least one planet has medium or high production.
- Penalize clusters near the sun if all approach routes are bad.
- Reward clusters closer to our owned planets than enemy owned planets.

Forward-base value build idea:

- A neutral near the enemy can be valuable even if its production is medium.
- Do not reward forward value early unless the route is safe and the source keeps reserve.
- In 4P, forward bases are riskier because they can drag us into fights with multiple players.

## Page 3: Reserve, Route Safety, Assignment Ledger, And Action Generation

The bot should never empty an important planet without reason. Reserve must be dynamic:

```text
base_reserve = max(5, production * 1.5)
incoming_reserve = incoming_enemy_ships * 1.25
phase_reserve = higher in late game if ahead
reserve = max(base_reserve, incoming_reserve, phase_reserve)
```

Opening exception:

```text
if step < 45 and no enemy fleet threatens source:
    reserve = max(5, production)
```

Route safety must be included from the start. At minimum:

- compute angle from source to target,
- compute source-to-target segment,
- reject direct segment if it intersects the sun before target collision,
- reject routes that obviously leave board bounds,
- reject targets requiring impossible travel timing.

Assignment ledger:

```python
target_need[target_id] = ships_required
target_planned[target_id] += ships_sent
source_available[source_id] -= ships_sent
```

Every candidate must check:

```text
remaining_need = target_need - target_planned
source_surplus = source_ships - source_reserve - source_spent
```

Only launch if:

```text
remaining_need > 0
source_surplus >= minimum_launch
candidate_score > threshold
route is safe
```

Action generation:

```python
move = [source_id, angle, ships]
```

Sort candidate moves by score and accept them while the ledger has ships. This lets the bot launch from multiple planets without double-spending.

## Page 4: Bite-Sized Implementation Tasks

### Task 1: Observation Parsing

**Files:**

- Create: `bots/expansion_snowball/main.py`
- Create: `tests/test_expansion_snowball.py`

- [ ] **Step 1: Write parsing tests**

```python
def test_parse_state_groups_planets_by_owner():
    obs = {"players": [0, 1], "step": 12, "planets": [
        {"id": 1, "owner": 0, "ships": 50, "production": 5, "x": 20, "y": 20, "radius": 3},
        {"id": 2, "owner": 1, "ships": 30, "production": 4, "x": 80, "y": 80, "radius": 3},
        {"id": 3, "owner": -1, "ships": 10, "production": 2, "x": 45, "y": 20, "radius": 2},
    ], "fleets": []}
    state = parse_state(obs)
    assert len(state["mine"]) == 1
    assert len(state["enemies"]) == 1
    assert len(state["neutral"]) == 1
```

- [ ] **Step 2: Implement `parse_state` with safe defaults**
- [ ] **Step 3: Run `pytest tests/test_expansion_snowball.py -v`**

### Task 2: Scoring Function

- [ ] **Step 1: Write tests for production, distance, cost, and sun penalty**
- [ ] **Step 2: Implement `score_target(source, target, state)`**
- [ ] **Step 3: Assert high-production safe targets beat weak targets**
- [ ] **Step 4: Assert sun-blocked targets return a losing score**

### Task 3: Reserve And Ledger

- [ ] **Step 1: Test that home keeps reserve in opening**
- [ ] **Step 2: Test incoming enemy fleets raise reserve**
- [ ] **Step 3: Test two sources do not oversend to one target**
- [ ] **Step 4: Implement source and target ledgers**

### Task 4: Agent Integration

- [ ] **Step 1: Build candidates from every owned source**
- [ ] **Step 2: Sort by score**
- [ ] **Step 3: Accept candidates that fit reserve and target need**
- [ ] **Step 4: Return only legal move lists**
- [ ] **Step 5: Run PvP smoke**

```powershell
.venv-ow\Scripts\python tools\run_pvp.py --agents bots/expansion_snowball/main.py bots/starter/main.py --seeds 1 2 3 4 5 --viewer-replays --focus-agent bots/expansion_snowball/main.py
```

## Page 5: Analytics, Tuning, Viewer Review, And Goals

Run batches and record:

- win rate,
- average production at step 80,
- average planet count at step 80,
- average ship delta at step 160,
- `slow_expansion` count,
- `idle_overstock` count,
- `bad_launch_sun_lane` count,
- `sun_death` count,
- first losing issue per replay.

Tuning matrix:

```text
PRODUCTION_WEIGHT: 10, 14, 18
TRAVEL_TURN_WEIGHT: 0.5, 0.7, 1.0
SHIP_COST_WEIGHT: 0.8, 1.0, 1.2
PAYBACK_LIMIT_EARLY: 35, 45, 55
RESERVE_MULTIPLIER: 1.0, 1.5, 2.0
CLUSTER_WEIGHT: 0, 4, 8
```

Viewer review checklist:

- At step 30, did home choose a strong first neutral?
- At step 60, does the bot own at least two useful planets?
- At step 100, are captured planets launching or hoarding?
- Did any launch enter the sun lane?
- Is the bot overpaying for weak targets?
- Is the bot ignoring enemy pressure?
- If it loses, was the first real error expansion, geometry, or defense?

High-end build ideas:

- Add map archetype detection: open map, sun-blocked map, cluster map, comet-heavy map.
- Add first-target memory so the bot does not switch targets every turn.
- Add enemy contest prediction by comparing enemy travel time to the same neutral.
- Add capture-chain planning where capturing planet A unlocks planet B.
- Add anti-overstock rule: if a planet is safe and has too many ships, force it to contribute to expansion or pressure.

## Edge Cases And Detection Rules

Account for these edge cases directly in the plan before tuning:

- **Two equally good first targets:** choose the safer route, then shorter travel, then higher production.
- **High-production target behind the sun:** reject until safe geometry can find an offset route.
- **Low-ship source with high production:** do not drain it just because it has a good angle. Production sources are long-term assets.
- **Enemy rush toward our home:** reserve rises before expansion launches are planned.
- **Enemy captures our chosen neutral first:** recompute target ownership every turn and stop sending if target value flips.
- **Target already has friendly fleets inbound:** subtract planned and in-flight ships from remaining need.
- **4P nearby enemy cluster:** expansion near one enemy should be penalized if another enemy can attack the new planet cheaply.
- **Endgame neutral bait:** do not capture neutral planets that cannot repay or swing score before game end.

Wire these local detection rules into replay review:

```text
slow_expansion_candidate:
  step >= 60
  my_planets <= 1
  safe_neutral_exists == true

idle_overstock_candidate:
  owned_planet_ships > reserve * 3
  safe_target_exists == true
  no_launch_from_planet_for_15_steps

overpay_candidate:
  ships_sent > ships_required * 1.5
  target_is_low_production == true

bad_chain_candidate:
  newly_captured_planet_has_surplus
  no_launch_from_new_planet_for_25_steps
```

These do not need to be perfect in the first bot. They need to make replay review faster. If a replay shows a loss, the goal is to identify the first strategic error within two minutes.

## Codex Execution Loop

Use this loop for every change:

1. Write or update one small test.
2. Run the focused test file.
3. Implement the smallest logic change.
4. Run the focused test file again.
5. Run a five-seed PvP smoke.
6. Open the worst replay in the viewer.
7. Record whether the change improved expansion, safety, or win rate.
8. Commit only if tests pass and the viewer does not reveal a new obvious flaw.

Suggested commit sequence:

```text
feat: add expansion bot state parsing
feat: add expansion target scoring
feat: add expansion reserve ledger
feat: add expansion launch planner
test: add expansion pvp smoke coverage
```

## Implementation Notes For The First Build

Keep the first version deterministic. Do not add randomness to break ties because replay analysis becomes harder. Use a stable tie order: higher score, lower route risk, lower travel time, lower target id. This makes repeated runs easier to compare.

Do not let the bot attack too early unless the attack is obviously free. The biggest purpose of this variant is to establish the economy floor. If pressure logic causes early production to fall, remove that pressure and keep the expansion engine pure. Pressure belongs in its own bot first, then adaptive meta can decide when to use it.

For 4P, avoid assuming the closest enemy is the only enemy. Expansion toward the center may look strong in 2P and become a trap in 4P. Add a multi-enemy contest penalty that rises when a neutral is close to two enemy clusters. In 4P, a slightly safer side expansion can outperform a central high-production grab that gets attacked by everyone.

When tuning, separate losses into buckets:

- lost because first target was wrong,
- lost because expansion was too slow,
- lost because reserve was too low,
- lost because route was unsafe,
- lost because enemy pressure was ignored,
- lost because late-game scoring was passive.

Only tune the weight connected to the bucket. If first target is wrong, tune production, distance, and payback. If reserve is wrong, tune reserve. If late scoring is passive, do not disturb opening weights.

## Detailed Goals At The Bottom

- Beat `bots/starter/main.py` over 100 rotated 2P games.
- Own at least 2 planets by step 60 in 80% of games.
- Lead starter production by step 100 in 65% of games.
- Reduce `slow_expansion` and `idle_overstock` compared with starter behavior.
- Keep `sun_death` no worse than the safe geometry baseline.
- Become the default baseline opponent for all later strategy variants.

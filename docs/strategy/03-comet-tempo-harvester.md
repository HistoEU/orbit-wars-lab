# Comet Tempo Harvester Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox syntax for tracking.

**Goal:** Build a one-file Orbit Wars bot that selectively captures profitable comets, denies enemy comet tempo, and keeps normal expansion strong enough that comet chasing does not become a weakness.

**Architecture:** The bot is a hybrid planner with comet parsing, comet future-position estimation, comet scoring, budget-limited launches, and normal expansion fallback.

**Tech Stack:** Python Kaggle agent in `bots/comet_tempo/main.py`, `pytest`, `tools/run_pvp.py`, replay analyzer issue flags, and viewer review around comet windows.

---

## File Structure

- Create: `bots/comet_tempo/main.py`
- Create: `tests/test_comet_tempo.py`
- Use existing: `tools/run_pvp.py`
- Use existing: `tools/analyze_run.py`
- Use existing: `viewer/index.html`
- Copy safe route helpers into this bot after `safe_geometry` is stable.

## Page 1: Strategic Identity And Mechanics Coverage

This bot should exploit temporary comet value without becoming distracted. The correct behavior is not "always chase comets." The correct behavior is "take comets that repay, deny comets the enemy would get cheaply, and ignore comets that cost the core game."

The bot must account for:

- comet planet IDs,
- comet path groups,
- current path index,
- remaining comet lifetime,
- comet current ships,
- comet production,
- comet future position,
- source-to-comet travel time,
- life remaining after arrival,
- enemy distance to comet,
- enemy ability to capture comet,
- safe route availability,
- source reserve,
- normal planet alternatives,
- game phase,
- whether comet capture creates a forward base.

Comet windows should be reviewed around important phases such as steps 50, 150, and 250 if those are common spawn timings in current replays. The exact step is less important than the principle: when comet opportunity appears, the bot should explicitly decide whether to take, deny, or skip.

## Page 2: Comet Valuation, Future Position, And Build Ideas

Comet score should be different from static planet score:

```text
score =
  life_after_capture * production * comet_life_weight
  + denial_value
  + forward_base_value
  + ship_cache_value
  - capture_cost
  - travel_turns * travel_weight
  - source_weakening_penalty
  - route_risk_penalty
```

Starting weights:

```python
COMET_LIFE_WEIGHT = 1.8
DENIAL_WEIGHT = 8.0
FORWARD_BASE_WEIGHT = 3.0
SHIP_CACHE_WEIGHT = 0.4
TRAVEL_WEIGHT = 1.2
SOURCE_WEAKENING_WEIGHT = 2.0
MIN_LIFE_AFTER_CAPTURE = 10
```

Future position solve:

1. Read comet current path index.
2. Estimate travel turns to current comet position.
3. Advance comet along path by travel turns.
4. Recompute route to future position.
5. Reject if arrival occurs after comet disappears.

Denial build idea:

- Estimate enemy best travel time to comet.
- Estimate whether enemy has enough surplus ships.
- If enemy can capture cheaply and comet is valuable, add denial score.
- Cap denial score so the bot does not ruin its economy to deny a mediocre comet.

Budget build idea:

```text
opening comet budget: max 30% surplus ships
midgame comet budget: max 50% surplus ships
late comet budget: only if immediate score or denial value
endgame comet budget: only if final score improves
```

Normal expansion fallback is mandatory. If no comet clears threshold, the bot should behave like a simpler expansion bot.

## Page 3: Planner Flow, Risk Filters, And Action Generation

Planner order:

1. Parse state and comet metadata.
2. Compute source reserves.
3. Build comet candidates.
4. Predict comet future positions.
5. Compute safe routes.
6. Score comet capture and denial.
7. Apply comet budget cap.
8. Reserve accepted moves in ledger.
9. Use remaining ships for normal expansion or defense.

Reject a comet candidate if:

- `life_after_capture < MIN_LIFE_AFTER_CAPTURE`,
- route crosses sun before target,
- capture cost exceeds source surplus,
- source is under incoming enemy pressure,
- static planet score is much better,
- enemy recapture risk is too high,
- comet path metadata is missing and route confidence is low.

Comet capture should usually come from the closest safe source. Multi-source comet captures are allowed only if:

- comet value is extremely high,
- no single source can capture safely,
- combined launch does not break reserves,
- target need ledger prevents overkill.

Action generation uses the same Kaggle format:

```python
[[source_id, angle, ships], ...]
```

## Page 4: Bite-Sized Implementation Tasks

### Task 1: Comet Metadata Parser

**Files:**

- Create: `bots/comet_tempo/main.py`
- Create: `tests/test_comet_tempo.py`

- [ ] **Step 1: Test comet IDs map to path indices**

```python
def test_comet_metadata_maps_id_to_path():
    obs = {"comet_planet_ids": [9], "paths": [[[10, 10], [11, 10], [12, 10]]], "path_index": {9: 1}}
    meta = parse_comets(obs)
    assert meta[9]["remaining_life"] == 2
```

- [ ] **Step 2: Implement parser with safe fallbacks**
- [ ] **Step 3: Test missing comet fields returns empty metadata**

### Task 2: Future Position And Life

- [ ] **Step 1: Test future comet position advances along path**
- [ ] **Step 2: Test arrival after expiration is rejected**
- [ ] **Step 3: Implement `comet_future_position` and `life_after_arrival`**

### Task 3: Comet Scoring

- [ ] **Step 1: Test long-life comet beats short-life comet**
- [ ] **Step 2: Test unsafe route loses**
- [ ] **Step 3: Test enemy denial raises score but stays capped**
- [ ] **Step 4: Implement `score_comet_candidate`**

### Task 4: Launch Planner And Fallback

- [ ] **Step 1: Test source reserve blocks comet launch**
- [ ] **Step 2: Test best comet move uses closest safe source**
- [ ] **Step 3: Implement comet budget cap**
- [ ] **Step 4: Implement normal expansion fallback**
- [ ] **Step 5: Run PvP smoke**

```powershell
.venv-ow\Scripts\python tools\run_pvp.py --agents bots/comet_tempo/main.py bots/starter/main.py --seeds 1 2 3 4 5 6 7 8 9 10 --viewer-replays --focus-agent bots/comet_tempo/main.py
```

## Page 5: Analytics, Tuning, Viewer Review, And Goals

Primary metrics:

- `missed_comet_window`,
- comet captures per game,
- good comet captures per game,
- production at step 120,
- ship delta after comet windows,
- slow expansion count,
- sun death count,
- win rate on comet-heavy seeds.

Viewer review checklist:

- Did the bot notice valuable comets?
- Did it skip bad comets for a good reason?
- Did arrival happen before expiration?
- Did comet capture weaken home or forward defense?
- Did the captured comet launch follow-up ships?
- Are missed comet flags true mistakes or acceptable skips?

Tuning knobs:

```text
MIN_LIFE_AFTER_CAPTURE: 6, 10, 15
COMET_LIFE_WEIGHT: 1.2, 1.8, 2.4
DENIAL_WEIGHT: 4, 8, 12
COMET_BUDGET_OPENING: 20%, 30%, 40%
COMET_BUDGET_MIDGAME: 35%, 50%, 65%
STATIC_PLANET_OVERRIDE_MARGIN: 10, 20, 35
```

High-end build ideas:

- Add comet opportunity classifier: free, contested, bait, late, dangerous, score-swing.
- Add enemy-denial planner that sends minimum ships to beat enemy timing.
- Add comet follow-up planner so captured comets immediately launch if useful.
- Add map memory of comet path patterns from previous frames.
- Add adaptive budget: spend more on comet when behind in production but ahead in local ship surplus.

## Edge Cases And Detection Rules

Account for these edge cases:

- **Comet expires before arrival:** reject even if production looks excellent.
- **Comet has high ships but low remaining life:** reject unless immediate score swing is strong.
- **Comet near enemy:** add denial value, but cap spending so the bot does not suicide for denial.
- **Comet route crosses sun:** reject unless safe geometry finds an offset route.
- **Comet capture weakens home:** defense reserve beats comet budget.
- **Comet metadata missing:** degrade to normal planet scoring with a penalty.
- **Enemy already inbound to comet:** compare arrival times and required ships before committing.
- **Captured comet becomes launch base:** use it only when it has surplus and enough remaining life.

Detection rules:

```text
missed_comet_window:
  good_comet_exists == true
  source_surplus_available == true
  safe_route_exists == true
  no_comet_launch_before_window_closes

bad_comet_chase:
  comet_life_after_capture < minimum
  ships_sent > comet_value_estimate

comet_overbudget:
  ships_sent_to_comets > allowed_phase_budget

comet_home_blunder:
  source_is_home
  home_falls_below_reserve
  enemy_pressure_exists
```

Viewer notes should distinguish between correct skips and mistakes. A skipped comet is correct if static expansion was better, route was unsafe, arrival was late, or defense needed the ships. A skipped comet is a flaw if it was safe, cheap, long-lived, and the bot had idle surplus.

## Codex Execution Loop

Use this loop:

1. Add a parser test for the exact comet metadata shape present in current replays.
2. Add a missing-metadata test so the agent never crashes.
3. Implement parser and future-position functions.
4. Add scoring tests for good, bad, contested, and late comets.
5. Add budget tests so comet spending cannot drain defense.
6. Run a ten-seed PvP smoke.
7. Open replays around comet windows and label each comet decision as take, deny, or skip.
8. Tune only after the labels show the decision model is reading opportunities correctly.

Suggested commit sequence:

```text
feat: add comet metadata parser
feat: add comet life and future position scoring
feat: add comet budgeted launch planner
feat: add comet fallback expansion behavior
test: add comet window replay checks
```

## Implementation Notes For The First Build

Make the comet planner conservative in version one. A comet bot that takes only obviously good comets is useful. A comet bot that takes every comet teaches us little because every loss looks like overchasing. The first version should skip many comets and capture the clean ones.

Use three labels in replay review:

```text
TAKE: comet was worth ships and route was safe
DENY: comet mainly mattered because enemy could get it
SKIP: comet was bad, late, unsafe, or less valuable than static expansion
```

For every missed comet flag, assign one label manually in the viewer. If the correct label is `SKIP`, the detector threshold may be too sensitive. If the correct label is `TAKE` or `DENY`, the bot needs a scoring or timing fix.

Do not let comet capture replace the expansion engine. The normal expansion fallback should run every turn after comet planning. If comet planning spends nothing, the bot should still play a coherent game. If comet planning spends some budget, the remaining ships should still expand or defend.

Enemy denial is the easiest part to overtune. A denied comet only matters if the enemy was actually likely to get value from it. Cap denial by comet lifetime and enemy capture cost. If the enemy would need to overpay badly, let them overpay.

Loss buckets for review:

- missed valuable comet,
- captured comet too late,
- overchased bad comet,
- comet route unsafe,
- home weakened by comet launch,
- comet captured but never used afterward,
- static expansion ignored because comet score was too high.

Tune only the bucket that appears repeatedly across seed batches.

## Success Review Matrix

Review comet behavior with this matrix:

```text
If missed comet flags fall and win rate rises:
  comet model is adding real tempo.

If missed comet flags fall and win rate drops:
  the bot is overchasing or weakening core expansion.

If missed comet flags stay high:
  parser, future-position estimate, or score threshold is wrong.

If comet captures happen too late:
  minimum life after capture is too low or travel estimate is optimistic.

If enemy gets easy comets:
  denial scoring is too weak or enemy travel estimate is missing.

If home gets punished after comet launch:
  comet budget is bypassing defense reserve.
```

The key review question is not "did we capture a comet?" It is "did that comet improve the next 50 turns?" A comet capture that causes home loss is bad. A skipped comet that lets us take two static planets can be correct.

One extra rule for the first implementation: every accepted comet launch should beat the best normal expansion candidate by either value or urgency. If it does not, normal expansion wins. This keeps the bot from treating comets as mandatory and makes the planner easier to trust.

## Detailed Goals At The Bottom

- Cut `missed_comet_window` by at least 60% where comets are truly valuable.
- Capture at least one good comet in 50% of games where a good comet exists.
- Keep production within 10% of the economy bot by step 120.
- Avoid increasing `sun_death` compared with safe geometry.
- Beat starter on seeds where starter ignores comet tempo.
- Produce a comet planner module suitable for adaptive meta.

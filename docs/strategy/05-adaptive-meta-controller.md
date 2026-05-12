# Adaptive Meta Controller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox syntax for tracking.

**Goal:** Build the main Orbit Wars submission candidate by combining expansion, safe geometry, comet tempo, pressure, defense, and endgame scoring under an inspectable mode controller.

**Architecture:** The bot is a deterministic controller with signal extraction, mode budgets, a source ship ledger, specialized planners, and a merge layer that prevents double-spending.

**Tech Stack:** Python Kaggle agent in `bots/adaptive_meta/main.py`, `pytest`, `tools/run_pvp.py`, `tools/compare_bots.py`, replay analyzer flags, and the local viewer.

---

## File Structure

- Create: `bots/adaptive_meta/main.py`
- Create: `tests/test_adaptive_meta.py`
- Use existing: `tools/run_pvp.py`
- Use existing: `tools/run_tournament.py`
- Use existing: `tools/compare_bots.py`
- Use existing: `tools/analyze_run.py`
- Use existing: `viewer/index.html`
- Copy stable helper logic from the four single-strategy bots into this one-file agent.

## Page 1: Strategic Identity And Mechanics Coverage

The adaptive bot should be built last. Its job is not to invent a new tactic. Its job is to decide which known tactic deserves ships in the current state. It should be the final candidate because it can expand when expansion is best, stay safe when geometry is dangerous, take comets when valuable, pressure when enemies are weak, defend when threatened, and score late.

The bot must account for:

- game phase,
- player count,
- my planet count,
- enemy planet counts,
- production delta,
- ship delta,
- fleet pressure,
- incoming threats,
- comet opportunities,
- route safety,
- source reserves,
- target ownership,
- late-game score swing,
- 2P direct enemy comparison,
- 4P politics,
- whether we are ahead or behind,
- issue patterns from replay analytics.

Modes:

```text
EXPAND
SAFE_CAPTURE
COMET
PRESSURE
DEFEND
ENDGAME_SCORE
HOLD
```

Controller rules:

- defense reserve always applies,
- no planner can spend the same ships twice,
- no target should receive pointless overkill,
- mode changes need hysteresis,
- safe route checks apply to every planner,
- 4P target selection differs from 2P,
- late game values immediate score more than long payback.

## Page 2: Signal Extraction, Mode Budgeting, And Build Ideas

Build `compute_game_state(obs)` first. It should produce:

```python
state = {
    "step": step,
    "player_id": my_id,
    "player_count": player_count,
    "my_planets": my_planets,
    "enemy_planets_by_owner": enemy_planets_by_owner,
    "neutral_planets": neutral_planets,
    "comet_planets": comet_planets,
    "my_fleets": my_fleets,
    "enemy_fleets": enemy_fleets,
}
```

Build `compute_signals(state)`:

```python
signals = {
    "phase": "mid",
    "production_delta": my_production - best_enemy_production,
    "ship_delta": my_total_ships - best_enemy_total_ships,
    "planet_delta": len(my_planets) - best_enemy_planet_count,
    "incoming_threat": total_incoming_enemy_ships,
    "good_comet_count": count_good_comets,
    "pressure_opportunity": best_pressure_score,
    "route_risk_level": route_risk_level,
    "is_ahead": score_delta > 20,
}
```

Mode budget table:

```text
early/even: expand 65, defend 20, comet 10, pressure 5
early/behind: expand 60, safe_capture 25, defend 10, pressure 5
mid/ahead: expand 25, defend 25, pressure 25, comet 25
mid/behind: pressure 35, expand 30, comet 20, defend 15
late/ahead: defend 45, endgame_score 30, pressure 15, comet 10
late/behind: pressure 55, endgame_score 25, comet 10, defend 10
4P/even: expand 45, defend 25, comet 15, pressure 15
4P/ahead: defend 40, score 25, expand 20, pressure 15
```

Build idea: mode hysteresis.

- Keep previous main mode for at least 5 turns unless there is a serious threat.
- Do not switch from pressure to expansion because of one small signal change.
- Emergency defense can override hysteresis.

## Page 3: Planner Interfaces, Ship Ledger, And Merge Layer

Every planner should return proposals, not final moves:

```python
proposal = {
    "planner": "PRESSURE",
    "source_id": 1,
    "target_id": 9,
    "angle": 1.4,
    "ships": 32,
    "score": 48.0,
    "risk": 2.0,
    "reason": "weak_high_production_enemy",
}
```

Source ledger:

```python
ledger = {
    source_id: {
        "ships": source_ships,
        "reserve": reserve,
        "spent": 0,
        "available": source_ships - reserve,
    }
}
```

Target ledger:

```python
target_ledger[target_id] = {
    "need": ships_required,
    "planned": ships_already_sent,
}
```

Merge rules:

1. Defense proposals reserve first.
2. Sort other proposals by planner budget and score.
3. Reject unsafe routes.
4. Reject proposals over planner budget.
5. Reject proposals that overspend source ledger.
6. Reject proposals that overfill target need without reason.
7. Accept legal proposals as Kaggle moves.

Planner modules inside one file:

```python
plan_defense(state, signals, ledger)
plan_expansion(state, signals, ledger)
plan_comets(state, signals, ledger)
plan_pressure(state, signals, ledger)
plan_endgame_score(state, signals, ledger)
merge_proposals(state, proposals, ledger)
```

The adaptive bot should be easy to debug by reading the proposals. Do not use black-box ML here. We need transparent decisions that can be fixed after one replay.

## Page 4: Bite-Sized Implementation Tasks

### Task 1: Signals

**Files:**

- Create: `bots/adaptive_meta/main.py`
- Create: `tests/test_adaptive_meta.py`

- [ ] **Step 1: Write tests for phase and player count**

```python
def test_compute_signals_detects_4p_midgame():
    obs = make_obs(step=180, players=[0, 1, 2, 3])
    state = compute_game_state(obs)
    signals = compute_signals(state)
    assert signals["phase"] == "mid"
    assert signals["player_count"] == 4
```

- [ ] **Step 2: Implement `compute_game_state`**
- [ ] **Step 3: Implement `compute_signals`**
- [ ] **Step 4: Test production, ship, and planet deltas**

### Task 2: Mode Budget

- [ ] **Step 1: Test early even budget favors expansion**
- [ ] **Step 2: Test late behind budget favors pressure**
- [ ] **Step 3: Test late ahead budget favors defense and scoring**
- [ ] **Step 4: Test 4P budget reduces tunnel-vision pressure**
- [ ] **Step 5: Implement `choose_mode_budget`**

### Task 3: Ledger And Merge

- [ ] **Step 1: Test ledger blocks double-spend**
- [ ] **Step 2: Test target ledger blocks overkill**
- [ ] **Step 3: Test defense proposals consume budget first**
- [ ] **Step 4: Implement `merge_proposals`**

### Task 4: Planner Integration

- [ ] **Step 1: Add expansion proposal generator**
- [ ] **Step 2: Add safe route checks to every proposal**
- [ ] **Step 3: Add comet proposal generator**
- [ ] **Step 4: Add pressure proposal generator**
- [ ] **Step 5: Add endgame score proposal generator**
- [ ] **Step 6: Run full tests**

### Task 5: League Evaluation

```powershell
.venv-ow\Scripts\python tools\run_pvp.py --agents bots/adaptive_meta/main.py bots/starter/main.py --seeds 1 2 3 4 5 6 7 8 9 10 --viewer-replays --focus-agent bots/adaptive_meta/main.py
.venv-ow\Scripts\python tools\run_pvp.py --agents bots/adaptive_meta/main.py bots/expansion_snowball/main.py --seeds 11 12 13 14 15 16 17 18 19 20 --viewer-replays --focus-agent bots/adaptive_meta/main.py
.venv-ow\Scripts\python tools\run_pvp.py --agents bots/adaptive_meta/main.py bots/starter/main.py bots/random_hold/main.py bots/random_hold/main.py --player-count 4 --seeds 21 22 23 24 25 --viewer-replays --focus-agent bots/adaptive_meta/main.py
```

## Page 5: Analytics, Tuning, Viewer Review, And Goals

Primary metrics:

- win rate against every internal bot,
- 2P and 4P performance,
- issue count by type,
- issue count by severity,
- production by phase,
- ship delta by phase,
- mode budget distribution,
- late-game score swing,
- comet decision quality,
- pressure decision quality,
- defense failure count.

Viewer review checklist:

- Does the chosen mode match what a human sees?
- When behind, does pressure actually increase?
- When ahead, does defense and scoring increase?
- Does the bot still expand when it needs production?
- Are comets selective and not addictive?
- Are pressure attacks meaningful?
- Does the bot avoid sun deaths across all planners?
- In 4P, does it avoid wasting all ships on one opponent?

High-end build ideas:

- Add mode reason logging into exported replays if the exporter can carry debug metadata.
- Add per-opponent threat ranking in 4P.
- Add adaptive risk tolerance based on issue history in current game.
- Add parameter sweep configs for budget tables.
- Add "champion gate": adaptive cannot replace baseline unless it wins broad seed batches and has equal or lower P1 issue rate.
- Add self-match testing between adaptive versions to avoid overfitting starter.

## Edge Cases And Detection Rules

Account for these edge cases:

- **Mode thrashing:** hysteresis prevents switching every turn.
- **Planner double-spend:** source ledger blocks spending the same ships twice.
- **Target overkill:** target ledger blocks redundant launches unless the attack is deliberately overwhelming.
- **Defense emergency:** defense overrides all non-defense budgets.
- **Comet addiction:** comet budget stays capped even when comet score is high.
- **Pressure tunnel vision in 4P:** target ranking considers third-party advantage.
- **Endgame bad payback:** expansion planner is restricted when a planet cannot repay before game end.
- **Safe geometry disagreement:** if route confidence is low, proposal risk rises or proposal is rejected.

Detection rules:

```text
mode_thrashing:
  main_mode_changes > 4 within 20 steps

double_spend_bug:
  total_ships_planned_from_source > source_surplus

budget_violation:
  planner_spend > planner_budget + tolerance

adaptive_confusion_loss:
  no dominant issue type
  mode switches frequently
  win probability steadily declines

late_wrong_mode:
  step > 350
  bot behind
  pressure_budget_low
  safe_pressure_target_exists
```

The adaptive bot should be promoted only when these failure signals are controlled. A bot that wins with random-looking decisions is dangerous because it will be hard to repair under deadline pressure.

## Codex Execution Loop

Use this loop:

1. Build and test signal extraction.
2. Build and test mode budgets.
3. Build and test source ledger.
4. Build and test target ledger.
5. Integrate expansion only.
6. Add safe geometry.
7. Add comet planner.
8. Add pressure planner.
9. Add defense and endgame planners.
10. Run league evaluation.
11. Review viewer losses before changing weights.
12. Promote only after broad seed improvement.

Suggested commit sequence:

```text
feat: add adaptive signal extraction
feat: add adaptive mode budgets
feat: add adaptive proposal ledger
feat: add adaptive expansion and defense planners
feat: add adaptive comet and pressure planners
feat: add adaptive league evaluation configs
```

Promotion rules:

- Unit tests pass.
- PvP smoke passes.
- 2P win rate improves over best single strategy.
- 4P smoke improves or stays stable.
- P0 issues are zero.
- P1 issues do not rise.
- Viewer review explains both wins and losses.

## Implementation Notes For The First Build

Build adaptive meta as a controller, not as a giant pile of special cases. The first version should combine only expansion, defense, and safe geometry. Once that is stable, add comet planning. Once comet planning is stable, add pressure. This staged approach makes regressions easy to isolate.

The most important debugging tool is proposal metadata. Even if Kaggle only receives move lists, local code should build proposals with planner name, reason, score, risk, and budget. The merge layer can discard metadata before returning moves. Tests can inspect proposals directly.

Avoid black-box weighting. Do not use a model or opaque optimizer in the first adaptive bot. The competition work needs fast diagnosis. If adaptive loses, we need to know whether it was in the wrong mode, chose the wrong target, overspent a source, missed a comet, or failed pressure.

Mode hysteresis should be simple:

```text
keep current strategic emphasis for 5 turns
override immediately for defense emergency
override immediately for endgame final score emergency
otherwise require signal margin before switching
```

When tuning adaptive, never tune all planners at once. Freeze four planners and adjust one. If a league result improves, run the same change against at least starter, expansion snowball, and 4P smoke before accepting it.

Loss buckets for review:

- signal extraction wrong,
- mode budget wrong,
- correct mode but bad planner proposal,
- planner proposal good but merge rejected it,
- ledger prevented a needed move,
- double-spend or overkill bug,
- 4P politics wrong,
- endgame scoring wrong.

Adaptive meta is ready only when losses can be explained cleanly. If every loss looks mysterious, the controller is too tangled.

## Success Review Matrix

Review adaptive meta with this matrix:

```text
If win rate improves and issue rate falls:
  promote candidate after wider seed run.

If win rate improves but P1 issues rise:
  keep as experiment, do not promote.

If issue rate falls but win rate drops:
  controller is too conservative.

If 2P improves and 4P drops:
  opponent selection and budget table need 4P tuning.

If mode thrashing appears:
  hysteresis is too weak or signals are too noisy.

If merge rejects good proposals:
  ledger or budget ordering is too strict.
```

The final bot should be measured like a league competitor. It needs to beat known opponents, survive bad map types, keep issue rates low, and produce losses that are understandable enough to fix the next day.

## Detailed Goals At The Bottom

- Beat the best single-strategy bot over 400 rotated 2P games.
- Perform better than any single-strategy bot in 4P smoke pools.
- Reduce slow expansion, missed comet, and late no-pressure flags together.
- Keep sun and bad-launch issues at safe-geometry levels.
- Produce decisions that are inspectable in tests and viewer analysis.
- Become the main Kaggle submission candidate after two clean daily cycles.

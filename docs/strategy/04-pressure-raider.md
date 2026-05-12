# Pressure Raider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox syntax for tracking.

**Goal:** Build a one-file Orbit Wars bot that applies tactical pressure, captures weak enemy value, punishes passive expansion, and avoids reckless all-in attacks.

**Architecture:** The bot is a defense-first pressure planner. It computes enemy vulnerability, protects its own key planets, budgets surplus ships for attacks, and uses safe routes before launching.

**Tech Stack:** Python Kaggle agent in `bots/pressure_raider/main.py`, `pytest`, `tools/run_pvp.py`, replay analyzer flags, and viewer review for attack quality.

---

## File Structure

- Create: `bots/pressure_raider/main.py`
- Create: `tests/test_pressure_raider.py`
- Use existing: `tools/run_pvp.py`
- Use existing: `tools/analyze_run.py`
- Use existing: `viewer/index.html`
- Copy safe route helpers into this bot after `safe_geometry` is stable.

## Page 1: Strategic Identity And Mechanics Coverage

This bot should win by making enemy plans inefficient. It should attack weak high-production planets, punish drained homes, deny reinforcement timing, and force opponents to spend ships defensively. It should not be a reckless attack bot. Pressure has value only when it changes the game state or enemy choices.

The bot must account for:

- enemy planet production,
- enemy planet ships,
- expected enemy production before arrival,
- our local surplus ships,
- our threatened planets,
- incoming enemy fleets,
- enemy fleet commitments,
- travel time,
- route safety,
- capture margin,
- attack budget by phase,
- 2P direct enemy comparison,
- 4P target politics,
- late-game score swing,
- whether holding is better than attacking.

Attack classes:

```text
capture_attack: enough ships to take target
harass_attack: small attack that forces response
denial_attack: blocks enemy capture or reinforcement
home_punish: hits drained enemy home
endgame_swing: improves final score immediately
```

Version one should focus on `capture_attack` and `home_punish`. Harassment and denial require more tuning because they can waste ships if they do not change enemy behavior.

## Page 2: Vulnerability Scoring, Pressure Budget, And Build Ideas

Vulnerability score:

```text
score =
  target_production * production_weight
  + enemy_ship_denial_value
  + enemy_home_bonus
  + forward_position_value
  + late_score_swing
  - ships_required
  - travel_turns * travel_weight
  - counterattack_risk
  - route_risk
```

Starting weights:

```python
ENEMY_PRODUCTION_WEIGHT = 12.0
ENEMY_SHIP_DENIAL_WEIGHT = 0.8
ENEMY_HOME_BONUS = 20.0
FORWARD_POSITION_WEIGHT = 2.0
LATE_SCORE_WEIGHT = 1.5
TRAVEL_WEIGHT = 1.0
COUNTER_RISK_WEIGHT = 2.5
```

Pressure budget:

```text
opening: 0-15% surplus ships
midgame even/ahead: 25-35% surplus ships
midgame behind: 35-45% surplus ships
late ahead: 15-25% surplus ships
late behind: 50-60% surplus ships
endgame: only score-swing attacks
```

Build idea: add an attack threshold that changes by phase:

```text
opening threshold: very high
midgame threshold: normal
late behind threshold: lower
late ahead threshold: high
```

Build idea: enemy home punish trigger:

- enemy home has launched recently or has low ships,
- our source is close enough,
- route is safe,
- we can send enough to beat production refill,
- attack does not expose our own home.

Build idea: 4P politics:

- avoid spending all pressure on the strongest player unless they are about to win,
- prefer exposed weak players for cheap value,
- avoid long fights that help untouched third parties,
- preserve enough ships for defense if multiple enemies are nearby.

## Page 3: Defense First, Attack Planner, And Action Generation

Defense must run before pressure. The order is:

1. Parse owned planets and enemy fleets.
2. Compute incoming threat per owned planet.
3. Set reserve for each source.
4. Mark threatened high-value planets.
5. Build pressure candidates from remaining surplus.
6. Reject candidates that break reserve.
7. Accept attacks through a source ledger.

Reserve model:

```text
reserve = max(base_reserve, incoming_enemy_ships * 1.25, production * 2)
```

Pressure candidate rejection:

- route is unsafe,
- source would fall below reserve,
- attack requires more than allowed budget,
- target production is too low,
- target refills before arrival,
- target can be reinforced faster than we arrive,
- in 4P the target choice creates bad tunnel vision,
- attack score is below phase threshold.

Action generation:

```python
for attack in sorted_attacks:
    if ledger.can_spend(attack.source_id, attack.ships):
        ledger.spend(attack.source_id, attack.ships)
        moves.append([attack.source_id, attack.angle, attack.ships])
```

Fallback behavior:

- If no good pressure exists, expand safely.
- If expansion is poor and we are ahead, reinforce.
- If behind late and no attack is good, launch only the safest score-swing move.

## Page 4: Bite-Sized Implementation Tasks

### Task 1: Enemy Vulnerability

**Files:**

- Create: `bots/pressure_raider/main.py`
- Create: `tests/test_pressure_raider.py`

- [ ] **Step 1: Write vulnerability tests**

```python
def test_high_production_low_garrison_scores_high():
    source = {"id": 1, "ships": 100, "production": 5, "x": 20, "y": 20}
    target = {"id": 8, "owner": 1, "ships": 12, "production": 6, "x": 35, "y": 20}
    score = pressure_score(source, target, {"step": 160, "player_count": 2})
    assert score > 0
```

- [ ] **Step 2: Implement `pressure_score`**
- [ ] **Step 3: Test low-production high-garrison target scores low**
- [ ] **Step 4: Test enemy home bonus applies only to real home target**

### Task 2: Defense Reserve

- [ ] **Step 1: Test incoming enemy fleets raise reserve**
- [ ] **Step 2: Test pressure cannot spend reserved ships**
- [ ] **Step 3: Implement `compute_reserves` and source ledger**

### Task 3: Attack Planner

- [ ] **Step 1: Test attack sends enough ships to capture**
- [ ] **Step 2: Test unsafe route rejects attack**
- [ ] **Step 3: Test late-behind mode lowers pressure threshold**
- [ ] **Step 4: Implement `plan_pressure`**

### Task 4: PvP And Viewer Review

- [ ] **Step 1: Run starter PvP**

```powershell
.venv-ow\Scripts\python tools\run_pvp.py --agents bots/pressure_raider/main.py bots/starter/main.py --seeds 1 2 3 4 5 6 7 8 9 10 --viewer-replays --focus-agent bots/pressure_raider/main.py
```

- [ ] **Step 2: Run against economy baseline**

```powershell
.venv-ow\Scripts\python tools\run_pvp.py --agents bots/pressure_raider/main.py bots/expansion_snowball/main.py --seeds 11 12 13 14 15 16 17 18 19 20 --viewer-replays --focus-agent bots/pressure_raider/main.py
```

- [ ] **Step 3: Review at least three wins and three losses in viewer**

## Page 5: Analytics, Tuning, Viewer Review, And Goals

Primary metrics:

- `late_trailing_no_pressure`,
- enemy high-production planets captured,
- pressure launches that capture,
- pressure launches that fail,
- vanished fleet count,
- final score swing after step 300,
- win rate versus economy bot,
- defense losses caused by overattacking.

Viewer review checklist:

- When behind late, does the bot attack meaningful targets?
- When ahead, does it avoid throwing?
- Does it target production or random low-value planets?
- Does it punish drained enemy home?
- Are attacks arriving before enemy production refills?
- Does it keep enough ships at home?
- In 4P, is it feeding one opponent while another grows?

Tuning knobs:

```text
ENEMY_PRODUCTION_WEIGHT: 8, 12, 16
PRESSURE_BUDGET_MID: 25%, 35%, 45%
PRESSURE_BUDGET_LATE_BEHIND: 45%, 60%, 75%
HOME_BONUS: 10, 20, 35
MIN_ATTACK_SCORE: 10, 20, 35
COUNTER_RISK_WEIGHT: 1.5, 2.5, 4.0
```

High-end build ideas:

- Add coordinated multi-source attacks against high-value planets.
- Add enemy refill prediction using target production and travel turns.
- Add attack timing after enemy launches.
- Add pressure heatmap to avoid overfighting one area.
- Add 4P opportunism: hit the weakest exposed target, not always the leader.
- Add final-score strike planner for last phase.

## Edge Cases And Detection Rules

Account for these edge cases:

- **Enemy target refills before arrival:** include production during travel in capture cost.
- **Enemy reinforcement arrives before us:** penalize or reject if visible fleets protect target.
- **Our source is threatened:** reserve blocks pressure spending.
- **Attack target is low production:** reject unless it creates immediate score swing.
- **Enemy home looks weak but route is unsafe:** reject.
- **We are ahead late:** pressure budget drops because throwing a lead is worse than missing a flashy capture.
- **We are behind late:** pressure threshold drops because passive loss is still loss.
- **4P dogpile risk:** do not attack the strongest opponent if a third player benefits more than we do.

Detection rules:

```text
late_trailing_no_pressure:
  step > 300
  ship_delta < -threshold
  safe_enemy_target_exists == true
  pressure_launch_count_recent == 0

bad_pressure_feed:
  attack_arrives
  target_not_captured
  ships_sent_large
  no enemy ships meaningfully removed

threw_lead:
  bot_was_ahead
  pressure_launch_drained_key_planet
  key_planet_lost_soon_after

missed_home_punish:
  enemy_home_ships_low
  safe_route_exists
  source_surplus_available
  no_attack_launched
```

These detection rules should be used to review losses. The pressure bot is not judged only by launches. It is judged by whether the launches changed the game.

## Codex Execution Loop

Use this loop:

1. Add a vulnerability scoring test.
2. Add a defense reserve test.
3. Implement pressure score and reserve.
4. Add a planner test for capture attacks.
5. Add a planner test for rejected reckless attacks.
6. Run five seeds against starter.
7. Run five seeds against expansion snowball.
8. Review one win where pressure worked and one loss where pressure failed.
9. Adjust thresholds only after the failure mode is named.

Suggested commit sequence:

```text
feat: add pressure vulnerability scoring
feat: add pressure defense budget
feat: add pressure capture planner
feat: add pressure phase thresholds
test: add pressure pvp smoke coverage
```

## Implementation Notes For The First Build

The first pressure bot should mostly launch capture attacks, not fake harassment. Harassment is hard to evaluate because a small attack might be useful even if it does not capture. Start with attacks where the success condition is clear: target captured, enemy loses ships, or final score improves.

Never plan pressure before defense. A pressure launch that looks brilliant but loses home is a losing move. The code structure should make this impossible by computing reserves first and giving pressure only surplus ships.

Pressure thresholds should depend on game state:

- ahead early: attack only if nearly free,
- behind early: expand first unless enemy target is exposed,
- ahead midgame: attack valuable targets but keep defense,
- behind midgame: accept more risk,
- ahead late: protect score and punish only weak targets,
- behind late: force action because passive loss is unacceptable.

For 4P, add opponent selection before target selection. The target should not simply be the closest enemy planet. Choose an opponent based on vulnerability, threat, and whether attacking them helps us more than it helps a third player.

Loss buckets for review:

- no pressure while behind,
- attack chosen but target was low value,
- attack arrived too late,
- attack drained a key source,
- attack fed enemy garrison,
- 4P attack helped another opponent,
- pressure worked but bot failed to follow up.

The viewer should be used to judge intent. If an attack captures a production planet and opens a forward base, it was probably good even if the game is later lost elsewhere. If an attack fails and does not force any response, it was likely bad.

## Success Review Matrix

Review pressure with this matrix:

```text
If late no-pressure falls and win rate rises:
  pressure is creating useful score swings.

If late no-pressure falls and win rate drops:
  attacks are too reckless or defense reserve is too low.

If pressure launches capture but no follow-up happens:
  forward-base logic is missing.

If attacks repeatedly fail by small margins:
  arrival production refill is underestimated.

If attacks fail by huge margins:
  target vulnerability scoring is wrong.

If 4P losses spike:
  opponent selection is causing tunnel vision.
```

The pressure bot should be evaluated on attack quality, not just attack count. A bot that launches constantly into bad targets is worse than a patient bot that attacks three times and changes the match.

One extra rule for the first implementation: every accepted pressure launch must have a named purpose. The purpose can be capture, home punish, denial, or endgame swing. If the planner cannot name the purpose, it should not launch.

That purpose should appear in local proposal metadata so replay review can separate smart aggression from random movement.

## Detailed Goals At The Bottom

- Reduce `late_trailing_no_pressure` by at least 70%.
- Capture enemy high-production planets in a meaningful share of wins.
- Beat expansion snowball in at least 45% of games while showing a distinct pressure style.
- Keep vanished fleet increase below 10% compared with safe geometry.
- Never spend defense reserve on pressure.
- Produce a pressure planner module suitable for adaptive meta.

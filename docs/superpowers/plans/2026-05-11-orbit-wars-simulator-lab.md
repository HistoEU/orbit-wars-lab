# Orbit Wars Simulator Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a month-long Orbit Wars simulator and tournament lab that can run many matches in parallel, mirror the official game mechanics for diagnostics, detect strategic and technical flaws, and produce submission decisions backed by evidence.

**Architecture:** Use the official Kaggle `orbit_wars` environment as the authoritative match runner, then build a deterministic mirror simulator beside it for state inspection, move validation, tactical regret checks, and replay analysis. Store every match, turn metric, issue, and bot version in SQLite/CSV artifacts so we can compare bot versions over hundreds or thousands of seeds.

**Tech Stack:** Python 3.11, `kaggle-environments` 1.29.1 from Kaggle source, current Kaggle CLI 2.1.2, standard-library `multiprocessing`, `sqlite3`, `csv`, `json`, `argparse`, plus `pytest` for verification.

---

## Scope And Success Criteria

This plan builds the lab, not the final championship bot. The lab is the machine that lets us produce the final bot with discipline.

The system must account for every game variable described in the official `official/README.md` and `official/agents.md`:

- Board size, origin, center, sun radius, sun collision, and out-of-bounds removal.
- Planet ownership, position, radius, ships, production, orbiting/static classification, initial positions, and angular velocity.
- Home planet setup across 2-player and 4-player matches.
- Fleet launch legality, multiple launches from one planet, launch offset, fleet speed, heading, straight-line movement, planet collision, moving-planet sweep collision, sun destruction, and out-of-bounds destruction.
- Comet spawning, comet expiration, comet paths, comet `path_index`, comet ownership, comet production, and comet removal with garrison loss.
- Official turn order: comet expiration, comet spawning, fleet launch, production, fleet movement/collision queue, planet rotation/comet movement/sweep collision, combat resolution.
- Combat grouping by owner, top-two attacker duel, tie removal, reinforcement, enemy capture, neutral capture, and simultaneous arrivals.
- Configuration values: `episodeSteps`, `actTimeout`, `runTimeout`, `agentTimeout`, `shipSpeed`, `sunRadius`, `boardSize`, and `cometSpeed`.
- Observation values: `player`, `planets`, `fleets`, `angular_velocity`, `initial_planets`, `comets`, `comet_planet_ids`, and `remainingOverageTime`.

The tournament lab must support:

- 2-player and 4-player matches.
- Player-slot rotation so a bot is tested from every start position.
- Parallel execution across CPU workers.
- Crash, timeout, invalid-action, and import-failure capture.
- Determinism checks using repeated seeds.
- Replay and log download hooks for submitted leaderboard episodes.
- Side-by-side comparison of bot versions.
- Parameter sweeps where each variant has a tracked identity.
- Issue detection that turns losses into specific flaws rather than vague frustration.

Top-10 success requires more than local win rate. The lab must produce answers to these questions before every submission:

- Does the candidate beat the current local champion over at least 400 two-player games and 400 four-player games?
- Does it maintain low crash/timeout rate over at least 1,000 total games?
- Does it improve one specific leaderboard hypothesis, such as better early expansion, stronger defense, or fewer sun deaths?
- Does it avoid regressions against public/reference agents and older internal agents?
- Does it show acceptable player-slot fairness?

---

## Month Build Plan

### Week 1: Authoritative Runner And Data Foundation

Build the folder structure, install dev dependencies, create the bot registry, run official environment matches, store results, and produce a readable summary. By the end of Week 1 we should be able to run `our_v1` against `starter` over 100 seeds and get a CSV plus SQLite record.

Primary deliverables:

- Bot registry under `bots/`.
- `tools/run_match.py`.
- `tools/run_tournament.py`.
- `src/orbitlab/storage.py`.
- `src/orbitlab/reporting.py`.
- First `runs/<timestamp>/summary.csv`.

### Week 2: Mirror Simulator And Mechanics Tests

Build a diagnostic mirror simulator that can step an observed state forward using candidate actions. It does not replace the Kaggle environment for final results. It exists to inspect why a move was good or bad and to detect logic errors in our bot.

Primary deliverables:

- `src/orbitlab/game_types.py`.
- `src/orbitlab/physics.py`.
- `src/orbitlab/collision.py`.
- `src/orbitlab/combat.py`.
- `src/orbitlab/mirror.py`.
- Unit tests for speed, rotation, sun collision, planet collision, combat, and turn order.

### Week 3: Issue Detection And Parallel Sweeps

Add detectors that classify flaws, then run many matches concurrently. Add parameter sweeps and regression gates so every candidate bot competes against baselines and prior versions.

Primary deliverables:

- `src/orbitlab/issues.py`.
- `src/orbitlab/detectors.py`.
- `src/orbitlab/scheduler.py`.
- `tools/sweep_params.py`.
- `tools/analyze_run.py`.
- Issue reports in Markdown and CSV.

### Week 4: Submission Loop And Leaderboard Diagnostics

Connect local runs to Kaggle submission monitoring. Pull episodes/logs/replays for submitted bots, attach issue classification, and use the same reporting format for local and leaderboard evidence.

Primary deliverables:

- `tools/submit_candidate.py`.
- `tools/fetch_episodes.py`.
- `tools/analyze_replay.py`.
- `submissions/<version>/main.py`.
- A daily submission checklist and a monthly retrospective report.

---

## File Structure

Create or modify these files:

```text
F:\kaggte bots\
  bots\
    starter\main.py
    random_hold\main.py
    our_v1\main.py
  config\
    tournament_default.json
    sweep_default.json
  docs\
    operations\
      daily-submission-checklist.md
      issue-taxonomy.md
  official\
    README.md
    agents.md
    main.py
  runs\
    .gitkeep
  src\
    orbitlab\
      __init__.py
      adapters.py
      bot_registry.py
      collision.py
      combat.py
      config.py
      detectors.py
      game_types.py
      issues.py
      mirror.py
      physics.py
      reporting.py
      scheduler.py
      storage.py
      tournament.py
  submissions\
    .gitkeep
  tests\
    unit\
      test_collision.py
      test_combat.py
      test_physics.py
      test_storage.py
    integration\
      test_run_match.py
      test_tournament_smoke.py
  tools\
    analyze_run.py
    analyze_replay.py
    fetch_episodes.py
    run_match.py
    run_tournament.py
    submit_candidate.py
    sweep_params.py
  requirements-ow-dev.txt
```

Responsibilities:

- `src/orbitlab/game_types.py`: immutable typed representations of planets, fleets, moves, observations, match results, and issue records.
- `src/orbitlab/physics.py`: board constants, distance math, fleet speed, launch point, planet rotation, comet prediction, and intercept helper functions.
- `src/orbitlab/collision.py`: segment-circle collision, sun collision, out-of-bounds detection, fleet-to-planet collision, and moving-planet sweep checks.
- `src/orbitlab/combat.py`: official combat resolution for grouped simultaneous arrivals.
- `src/orbitlab/mirror.py`: diagnostic simulator for one turn and short-horizon projections.
- `src/orbitlab/adapters.py`: conversion between Kaggle observations and our typed objects.
- `src/orbitlab/tournament.py`: single-match and series execution using the official Kaggle environment.
- `src/orbitlab/scheduler.py`: parallel worker orchestration and retry handling.
- `src/orbitlab/storage.py`: SQLite schema and CSV artifact writing.
- `src/orbitlab/detectors.py`: flaw detection after matches and per-turn analysis.
- `src/orbitlab/reporting.py`: summaries, leaderboard-style tables, and Markdown reports.
- `tools/*.py`: thin CLI wrappers that call `src/orbitlab` modules.
- `bots/*/main.py`: Kaggle-compatible agents.
- `tests/*`: verification for every mechanic and runner behavior.

---

## Data Model

Use SQLite as the durable run database, plus CSV for quick spreadsheet inspection.

Database path per run:

```text
runs/2026-05-11_160000_our_v1_gauntlet/results.sqlite
```

Tables:

```sql
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    label TEXT NOT NULL,
    config_json TEXT NOT NULL
);

CREATE TABLE bots (
    bot_id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE matches (
    match_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    seed INTEGER NOT NULL,
    player_count INTEGER NOT NULL,
    slots_json TEXT NOT NULL,
    rewards_json TEXT NOT NULL,
    statuses_json TEXT NOT NULL,
    steps INTEGER NOT NULL,
    winner_slot INTEGER,
    elapsed_seconds REAL NOT NULL,
    replay_path TEXT,
    error_text TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

CREATE TABLE turn_metrics (
    match_id TEXT NOT NULL,
    step INTEGER NOT NULL,
    slot INTEGER NOT NULL,
    planets INTEGER NOT NULL,
    ships_on_planets REAL NOT NULL,
    ships_in_fleets REAL NOT NULL,
    production INTEGER NOT NULL,
    fleets INTEGER NOT NULL,
    PRIMARY KEY(match_id, step, slot)
);

CREATE TABLE issues (
    issue_id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL,
    detector TEXT NOT NULL,
    severity TEXT NOT NULL,
    step INTEGER,
    slot INTEGER,
    message TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY(match_id) REFERENCES matches(match_id)
);
```

CSV artifacts:

```text
summary.csv       # one row per bot matchup
matches.csv       # one row per match
issues.csv        # one row per issue
turn_metrics.csv  # sampled or complete per-turn metrics
```

Severity levels:

- `P0`: bot crashes, times out, imports fail, or returns invalid action format.
- `P1`: tactical flaw likely caused a loss, such as repeated sun deaths or undefended high-production planet.
- `P2`: strategic weakness, such as low expansion rate or over-conservative reserves.
- `P3`: informational anomaly, such as player-slot bias that needs more seeds.

---

## Task 1: Dependency And Skeleton Setup

**Files:**
- Create: `requirements-ow-dev.txt`
- Create: `src/orbitlab/__init__.py`
- Create: `runs/.gitkeep`
- Create: `submissions/.gitkeep`
- Create: `bots/starter/main.py`
- Create: `bots/random_hold/main.py`
- Test: `tests/integration/test_tournament_smoke.py`

- [ ] **Step 1: Write the dependency file**

Create `requirements-ow-dev.txt`:

```text
pytest==8.4.2
```

- [ ] **Step 2: Install dev dependency**

Run:

```powershell
.\.venv-ow\Scripts\python -m pip install -r requirements-ow-dev.txt
```

Expected: `Successfully installed pytest-8.4.2` or `Requirement already satisfied`.

- [ ] **Step 3: Copy the official starter bot into the registry**

Create `bots/starter/main.py` by copying the content from `official/main.py`.

- [ ] **Step 4: Create a passive baseline bot**

Create `bots/random_hold/main.py`:

```python
def agent(obs, config=None):
    return []
```

- [ ] **Step 5: Create package marker and artifact directories**

Create `src/orbitlab/__init__.py`:

```python
__all__ = []
```

Create empty marker files:

```text
runs/.gitkeep
submissions/.gitkeep
```

- [ ] **Step 6: Write the first integration smoke test**

Create `tests/integration/test_tournament_smoke.py`:

```python
from kaggle_environments import make


def test_official_starter_beats_hold_bot_on_seed_42():
    env = make("orbit_wars", configuration={"seed": 42}, debug=True)
    env.run(["bots/starter/main.py", "bots/random_hold/main.py"])
    final = env.steps[-1]
    assert final[0].status == "DONE"
    assert final[1].status == "DONE"
    assert final[0].reward == 1
    assert final[1].reward == -1
```

- [ ] **Step 7: Run the smoke test**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\integration\test_tournament_smoke.py -v
```

Expected: `1 passed`. Warnings about unrelated Kaggle environments are acceptable if the test passes.

- [ ] **Step 8: Commit**

Run:

```powershell
git add requirements-ow-dev.txt src bots runs submissions tests
git commit -m "test: add orbit wars lab smoke baseline"
```

Expected: commit succeeds if this workspace is a Git repo. If it is not a Git repo, record the command output in `runs/manual-notes.md` after Task 7 adds reporting utilities.

---

## Task 2: Canonical Types And Adapters

**Files:**
- Create: `src/orbitlab/game_types.py`
- Create: `src/orbitlab/adapters.py`
- Test: `tests/unit/test_physics.py`

- [ ] **Step 1: Write canonical types**

Create `src/orbitlab/game_types.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlanetState:
    id: int
    owner: int
    x: float
    y: float
    radius: float
    ships: float
    production: int


@dataclass(frozen=True)
class FleetState:
    id: int
    owner: int
    x: float
    y: float
    angle: float
    from_planet_id: int
    ships: int


@dataclass(frozen=True)
class Move:
    from_planet_id: int
    angle: float
    ships: int


@dataclass(frozen=True)
class ObservationState:
    player: int
    planets: tuple[PlanetState, ...]
    fleets: tuple[FleetState, ...]
    angular_velocity: float
    initial_planets: tuple[PlanetState, ...]
    comets: tuple[dict[str, Any], ...]
    comet_planet_ids: frozenset[int]
    remaining_overage_time: float | None
```

- [ ] **Step 2: Write adapters**

Create `src/orbitlab/adapters.py`:

```python
from __future__ import annotations

from typing import Any

from .game_types import FleetState, Move, ObservationState, PlanetState


def read_field(obs: Any, key: str, default: Any) -> Any:
    if isinstance(obs, dict):
        return obs.get(key, default)
    return getattr(obs, key, default)


def parse_planet(raw: list[Any] | tuple[Any, ...]) -> PlanetState:
    return PlanetState(
        id=int(raw[0]),
        owner=int(raw[1]),
        x=float(raw[2]),
        y=float(raw[3]),
        radius=float(raw[4]),
        ships=float(raw[5]),
        production=int(raw[6]),
    )


def parse_fleet(raw: list[Any] | tuple[Any, ...]) -> FleetState:
    return FleetState(
        id=int(raw[0]),
        owner=int(raw[1]),
        x=float(raw[2]),
        y=float(raw[3]),
        angle=float(raw[4]),
        from_planet_id=int(raw[5]),
        ships=int(raw[6]),
    )


def parse_observation(obs: Any) -> ObservationState:
    return ObservationState(
        player=int(read_field(obs, "player", 0)),
        planets=tuple(parse_planet(p) for p in read_field(obs, "planets", [])),
        fleets=tuple(parse_fleet(f) for f in read_field(obs, "fleets", [])),
        angular_velocity=float(read_field(obs, "angular_velocity", 0.0)),
        initial_planets=tuple(parse_planet(p) for p in read_field(obs, "initial_planets", [])),
        comets=tuple(read_field(obs, "comets", [])),
        comet_planet_ids=frozenset(int(x) for x in read_field(obs, "comet_planet_ids", [])),
        remaining_overage_time=read_field(obs, "remainingOverageTime", None),
    )


def encode_move(move: Move) -> list[float | int]:
    return [int(move.from_planet_id), float(move.angle), int(move.ships)]
```

- [ ] **Step 3: Write adapter tests**

Append to `tests/unit/test_physics.py`:

```python
from src.orbitlab.adapters import parse_observation


def test_parse_observation_from_dict():
    obs = {
        "player": 2,
        "planets": [[1, 2, 10.0, 20.0, 2.0, 15, 3]],
        "fleets": [[5, 2, 11.0, 22.0, 0.5, 1, 7]],
        "angular_velocity": 0.035,
        "initial_planets": [[1, 2, 10.0, 20.0, 2.0, 15, 3]],
        "comets": [{"planet_ids": [99], "paths": [[[1.0, 2.0]]], "path_index": 0}],
        "comet_planet_ids": [99],
    }
    parsed = parse_observation(obs)
    assert parsed.player == 2
    assert parsed.planets[0].production == 3
    assert parsed.fleets[0].ships == 7
    assert 99 in parsed.comet_planet_ids
```

- [ ] **Step 4: Run adapter tests**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\unit\test_physics.py -v
```

Expected: all tests in the file pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/orbitlab/game_types.py src/orbitlab/adapters.py tests/unit/test_physics.py
git commit -m "feat: add orbit wars canonical state adapters"
```

---

## Task 3: Physics Engine

**Files:**
- Create: `src/orbitlab/physics.py`
- Modify: `tests/unit/test_physics.py`

- [ ] **Step 1: Write failing physics tests**

Add to `tests/unit/test_physics.py`:

```python
import math

from src.orbitlab.game_types import PlanetState
from src.orbitlab.physics import (
    BOARD_SIZE,
    CENTER,
    ROTATION_RADIUS_LIMIT,
    distance,
    fleet_speed,
    is_orbiting,
    launch_point,
    predict_planet_position,
)


def test_fleet_speed_matches_official_formula():
    expected = 1.0 + 5.0 * ((math.log(100) / math.log(1000.0)) ** 1.5)
    assert fleet_speed(100) == expected
    assert fleet_speed(1) == 1.0


def test_static_planet_does_not_rotate():
    planet = PlanetState(1, -1, 95.0, 50.0, 2.0, 10, 1)
    initial = {planet.id: planet}
    assert not is_orbiting(planet)
    assert predict_planet_position(planet, initial, 0.05, 20) == (95.0, 50.0)


def test_inner_planet_rotates_from_current_position():
    planet = PlanetState(1, -1, 70.0, 50.0, 2.0, 10, 1)
    initial = {planet.id: planet}
    x, y = predict_planet_position(planet, initial, math.pi / 2, 1)
    assert round(x, 6) == CENTER
    assert round(y, 6) == 70.0


def test_launch_point_starts_outside_source_radius():
    x, y = launch_point(10.0, 20.0, 3.0, 0.0)
    assert x == 13.1
    assert y == 20.0
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\unit\test_physics.py -v
```

Expected: imports fail for `src.orbitlab.physics`.

- [ ] **Step 3: Implement physics**

Create `src/orbitlab/physics.py`:

```python
from __future__ import annotations

import math

from .game_types import PlanetState

BOARD_SIZE = 100.0
CENTER = 50.0
SUN_RADIUS = 10.0
MAX_SPEED = 6.0
ROTATION_RADIUS_LIMIT = 50.0
LAUNCH_CLEARANCE = 0.1


def distance(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def orbital_radius(planet: PlanetState) -> float:
    return distance(planet.x, planet.y, CENTER, CENTER)


def is_orbiting(planet: PlanetState) -> bool:
    return orbital_radius(planet) + planet.radius < ROTATION_RADIUS_LIMIT


def fleet_speed(ships: int | float) -> float:
    ships = max(1.0, float(ships))
    ratio = math.log(ships) / math.log(1000.0)
    ratio = max(0.0, min(1.0, ratio))
    return 1.0 + (MAX_SPEED - 1.0) * (ratio ** 1.5)


def launch_point(sx: float, sy: float, radius: float, angle: float) -> tuple[float, float]:
    clearance = radius + LAUNCH_CLEARANCE
    return sx + math.cos(angle) * clearance, sy + math.sin(angle) * clearance


def predict_planet_position(
    planet: PlanetState,
    initial_by_id: dict[int, PlanetState],
    angular_velocity: float,
    turns: int | float,
) -> tuple[float, float]:
    initial = initial_by_id.get(planet.id, planet)
    if not is_orbiting(initial):
        return planet.x, planet.y
    radius = orbital_radius(initial)
    current_angle = math.atan2(planet.y - CENTER, planet.x - CENTER)
    future_angle = current_angle + angular_velocity * turns
    return CENTER + radius * math.cos(future_angle), CENTER + radius * math.sin(future_angle)
```

- [ ] **Step 4: Run physics tests**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\unit\test_physics.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/orbitlab/physics.py tests/unit/test_physics.py
git commit -m "feat: implement orbit wars physics primitives"
```

---

## Task 4: Collision Engine

**Files:**
- Create: `src/orbitlab/collision.py`
- Create: `tests/unit/test_collision.py`

- [ ] **Step 1: Write collision tests**

Create `tests/unit/test_collision.py`:

```python
from src.orbitlab.collision import (
    is_out_of_bounds,
    segment_circle_distance,
    segment_hits_circle,
    segment_hits_sun,
)


def test_segment_circle_distance_for_crossing_segment():
    assert segment_circle_distance(50.0, 50.0, 0.0, 50.0, 100.0, 50.0) == 0.0


def test_segment_hits_sun_when_crossing_center():
    assert segment_hits_sun(0.0, 50.0, 100.0, 50.0)


def test_segment_does_not_hit_sun_when_clear():
    assert not segment_hits_sun(0.0, 0.0, 100.0, 0.0)


def test_out_of_bounds_detection():
    assert is_out_of_bounds(-0.1, 50.0)
    assert is_out_of_bounds(50.0, 100.1)
    assert not is_out_of_bounds(50.0, 50.0)


def test_segment_hits_planet_radius():
    assert segment_hits_circle(10.0, 10.0, 5.0, 0.0, 10.0, 20.0, 10.0)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\unit\test_collision.py -v
```

Expected: import failure for `src.orbitlab.collision`.

- [ ] **Step 3: Implement collision functions**

Create `src/orbitlab/collision.py`:

```python
from __future__ import annotations

import math

from .physics import BOARD_SIZE, CENTER, SUN_RADIUS


def segment_circle_distance(
    cx: float,
    cy: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return math.hypot(cx - x1, cy - y1)
    t = ((cx - x1) * dx + (cy - y1) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    px = x1 + t * dx
    py = y1 + t * dy
    return math.hypot(cx - px, cy - py)


def segment_hits_circle(
    cx: float,
    cy: float,
    radius: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> bool:
    return segment_circle_distance(cx, cy, x1, y1, x2, y2) <= radius


def segment_hits_sun(x1: float, y1: float, x2: float, y2: float) -> bool:
    return segment_hits_circle(CENTER, CENTER, SUN_RADIUS, x1, y1, x2, y2)


def is_out_of_bounds(x: float, y: float) -> bool:
    return x < 0.0 or y < 0.0 or x > BOARD_SIZE or y > BOARD_SIZE
```

- [ ] **Step 4: Run collision tests**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\unit\test_collision.py -v
```

Expected: all collision tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/orbitlab/collision.py tests/unit/test_collision.py
git commit -m "feat: add orbit wars collision primitives"
```

---

## Task 5: Combat Engine

**Files:**
- Create: `src/orbitlab/combat.py`
- Create: `tests/unit/test_combat.py`

- [ ] **Step 1: Write combat tests**

Create `tests/unit/test_combat.py`:

```python
from src.orbitlab.combat import resolve_combat


def test_single_enemy_captures_when_surplus_exceeds_garrison():
    owner, ships = resolve_combat(owner=0, garrison=10, arrivals=[(1, 18)])
    assert owner == 1
    assert ships == 8


def test_single_enemy_damages_without_capture():
    owner, ships = resolve_combat(owner=0, garrison=10, arrivals=[(1, 7)])
    assert owner == 0
    assert ships == 3


def test_friendly_arrival_reinforces():
    owner, ships = resolve_combat(owner=0, garrison=10, arrivals=[(0, 5)])
    assert owner == 0
    assert ships == 15


def test_top_two_attackers_duel_before_planet_combat():
    owner, ships = resolve_combat(owner=0, garrison=10, arrivals=[(1, 20), (2, 13)])
    assert owner == 0
    assert ships == 3


def test_tied_top_attackers_destroy_each_other():
    owner, ships = resolve_combat(owner=0, garrison=10, arrivals=[(1, 20), (2, 20), (3, 5)])
    assert owner == 0
    assert ships == 10


def test_same_owner_arrivals_are_grouped():
    owner, ships = resolve_combat(owner=0, garrison=10, arrivals=[(1, 6), (1, 7)])
    assert owner == 1
    assert ships == 3
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\unit\test_combat.py -v
```

Expected: import failure for `src.orbitlab.combat`.

- [ ] **Step 3: Implement official combat**

Create `src/orbitlab/combat.py`:

```python
from __future__ import annotations

from collections import defaultdict


def resolve_combat(owner: int, garrison: float, arrivals: list[tuple[int, int]]) -> tuple[int, float]:
    grouped: dict[int, int] = defaultdict(int)
    for arrival_owner, ships in arrivals:
        if ships > 0:
            grouped[int(arrival_owner)] += int(ships)

    if not grouped:
        return owner, max(0.0, garrison)

    ranked = sorted(grouped.items(), key=lambda item: item[1], reverse=True)
    top_owner, top_ships = ranked[0]

    if len(ranked) > 1:
        second_ships = ranked[1][1]
        if top_ships == second_ships:
            return owner, max(0.0, garrison)
        survivor_owner = top_owner
        survivor_ships = top_ships - second_ships
    else:
        survivor_owner = top_owner
        survivor_ships = top_ships

    if survivor_owner == owner:
        return owner, garrison + survivor_ships

    remaining_garrison = garrison - survivor_ships
    if remaining_garrison < 0:
        return survivor_owner, -remaining_garrison
    return owner, remaining_garrison
```

- [ ] **Step 4: Run combat tests**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\unit\test_combat.py -v
```

Expected: all combat tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/orbitlab/combat.py tests/unit/test_combat.py
git commit -m "feat: mirror orbit wars combat resolution"
```

---

## Task 6: Move Validation

**Files:**
- Create: `src/orbitlab/validators.py`
- Test: `tests/unit/test_validators.py`

- [ ] **Step 1: Write validator tests**

Create `tests/unit/test_validators.py`:

```python
from src.orbitlab.game_types import Move, PlanetState
from src.orbitlab.validators import validate_moves


def test_rejects_launch_from_enemy_planet():
    planets = (PlanetState(1, 0, 10, 10, 2, 10, 1),)
    issues = validate_moves(player=1, planets=planets, moves=[Move(1, 0.0, 3)])
    assert issues[0].code == "launch_from_unowned_planet"


def test_rejects_overlaunch_across_multiple_moves():
    planets = (PlanetState(1, 0, 10, 10, 2, 10, 1),)
    issues = validate_moves(player=0, planets=planets, moves=[Move(1, 0.0, 7), Move(1, 1.0, 7)])
    assert issues[0].code == "overlaunch"


def test_accepts_multiple_legal_launches_from_same_planet():
    planets = (PlanetState(1, 0, 10, 10, 2, 10, 1),)
    issues = validate_moves(player=0, planets=planets, moves=[Move(1, 0.0, 4), Move(1, 1.0, 5)])
    assert issues == []
```

- [ ] **Step 2: Implement validator**

Create `src/orbitlab/validators.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict

from .game_types import Move, PlanetState


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    planet_id: int | None = None


def validate_moves(player: int, planets: tuple[PlanetState, ...], moves: list[Move]) -> list[ValidationIssue]:
    planet_by_id = {planet.id: planet for planet in planets}
    launched: dict[int, int] = defaultdict(int)
    issues: list[ValidationIssue] = []

    for move in moves:
        planet = planet_by_id.get(move.from_planet_id)
        if planet is None:
            issues.append(ValidationIssue("unknown_source_planet", "Move references a missing planet.", move.from_planet_id))
            continue
        if planet.owner != player:
            issues.append(ValidationIssue("launch_from_unowned_planet", "Move launches from a planet not owned by this player.", planet.id))
            continue
        if move.ships <= 0:
            issues.append(ValidationIssue("nonpositive_launch", "Move launches zero or negative ships.", planet.id))
            continue
        launched[planet.id] += move.ships
        if launched[planet.id] > int(planet.ships):
            issues.append(ValidationIssue("overlaunch", "Combined launches exceed available garrison.", planet.id))

    return issues
```

- [ ] **Step 3: Run validator tests**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\unit\test_validators.py -v
```

Expected: all validator tests pass.

- [ ] **Step 4: Commit**

Run:

```powershell
git add src/orbitlab/validators.py tests/unit/test_validators.py
git commit -m "feat: validate orbit wars move legality"
```

---

## Task 7: Mirror Simulator First Turn

**Files:**
- Create: `src/orbitlab/mirror.py`
- Test: `tests/unit/test_mirror.py`

- [ ] **Step 1: Write first-turn mirror tests**

Create `tests/unit/test_mirror.py`:

```python
from src.orbitlab.game_types import Move, ObservationState, PlanetState
from src.orbitlab.mirror import step_once


def test_owned_planet_produces_after_launch():
    obs = ObservationState(
        player=0,
        planets=(PlanetState(1, 0, 10, 10, 2, 10, 3), PlanetState(2, -1, 30, 10, 2, 5, 1)),
        fleets=(),
        angular_velocity=0.0,
        initial_planets=(PlanetState(1, 0, 10, 10, 2, 10, 3), PlanetState(2, -1, 30, 10, 2, 5, 1)),
        comets=(),
        comet_planet_ids=frozenset(),
        remaining_overage_time=None,
    )
    next_state = step_once(obs, {0: [Move(1, 0.0, 4)]})
    source = next(p for p in next_state.planets if p.id == 1)
    assert source.ships == 9
    assert len(next_state.fleets) == 1
```

- [ ] **Step 2: Implement first-turn simulator**

Create `src/orbitlab/mirror.py`:

```python
from __future__ import annotations

import itertools
import math

from .game_types import FleetState, Move, ObservationState, PlanetState
from .physics import fleet_speed, launch_point


def step_once(state: ObservationState, actions_by_player: dict[int, list[Move]]) -> ObservationState:
    planets_by_id = {planet.id: planet for planet in state.planets}
    next_planets = {planet.id: planet for planet in state.planets}
    next_fleets = list(state.fleets)
    next_fleet_id = 1 + max((fleet.id for fleet in state.fleets), default=0)

    for player, moves in actions_by_player.items():
        launched_by_planet: dict[int, int] = {}
        for move in moves:
            planet = next_planets.get(move.from_planet_id)
            if planet is None or planet.owner != player or move.ships <= 0:
                continue
            already = launched_by_planet.get(planet.id, 0)
            send = min(int(move.ships), int(planet.ships) - already)
            if send <= 0:
                continue
            launched_by_planet[planet.id] = already + send
            sx, sy = launch_point(planet.x, planet.y, planet.radius, move.angle)
            next_fleets.append(FleetState(next_fleet_id, player, sx, sy, float(move.angle), planet.id, send))
            next_fleet_id += 1
        for planet_id, sent in launched_by_planet.items():
            planet = next_planets[planet_id]
            next_planets[planet_id] = PlanetState(
                planet.id, planet.owner, planet.x, planet.y, planet.radius, planet.ships - sent, planet.production
            )

    for planet in tuple(next_planets.values()):
        if planet.owner != -1:
            next_planets[planet.id] = PlanetState(
                planet.id, planet.owner, planet.x, planet.y, planet.radius, planet.ships + planet.production, planet.production
            )

    moved_fleets = []
    for fleet in next_fleets:
        speed = fleet_speed(fleet.ships)
        moved_fleets.append(
            FleetState(
                fleet.id,
                fleet.owner,
                fleet.x + math.cos(fleet.angle) * speed,
                fleet.y + math.sin(fleet.angle) * speed,
                fleet.angle,
                fleet.from_planet_id,
                fleet.ships,
            )
        )

    return ObservationState(
        player=state.player,
        planets=tuple(sorted(next_planets.values(), key=lambda planet: planet.id)),
        fleets=tuple(moved_fleets),
        angular_velocity=state.angular_velocity,
        initial_planets=state.initial_planets,
        comets=state.comets,
        comet_planet_ids=state.comet_planet_ids,
        remaining_overage_time=state.remaining_overage_time,
    )
```

- [ ] **Step 3: Run mirror test**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\unit\test_mirror.py -v
```

Expected: all mirror tests pass.

- [ ] **Step 4: Expand mirror in Week 2**

After this first version passes, extend `step_once` in separate commits to include:

- Sun destruction using `segment_hits_sun`.
- Out-of-bounds removal using `is_out_of_bounds`.
- Planet collision queue using `segment_hits_circle`.
- Planet rotation after fleet movement.
- Moving-planet sweep collision.
- Combat resolution using `resolve_combat`.
- Comet path advancement and expiration using `comets` and `comet_planet_ids`.

Each extension gets its own failing unit test before implementation.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/orbitlab/mirror.py tests/unit/test_mirror.py
git commit -m "feat: add first-turn diagnostic mirror simulator"
```

---

## Task 8: Authoritative Match Runner

**Files:**
- Create: `src/orbitlab/tournament.py`
- Create: `tools/run_match.py`
- Test: `tests/integration/test_run_match.py`

- [ ] **Step 1: Write match-runner integration test**

Create `tests/integration/test_run_match.py`:

```python
from src.orbitlab.tournament import run_match


def test_run_match_returns_rewards_and_statuses():
    result = run_match(
        seed=42,
        agents=["bots/starter/main.py", "bots/random_hold/main.py"],
        player_count=2,
        debug=True,
    )
    assert result["seed"] == 42
    assert result["rewards"] == [1, -1]
    assert result["statuses"] == ["DONE", "DONE"]
    assert result["steps"] > 0
```

- [ ] **Step 2: Implement match runner**

Create `src/orbitlab/tournament.py`:

```python
from __future__ import annotations

import time
from typing import Any

from kaggle_environments import make


def run_match(seed: int, agents: list[str], player_count: int, debug: bool = True) -> dict[str, Any]:
    start = time.perf_counter()
    env = make("orbit_wars", configuration={"seed": int(seed)}, debug=debug)
    env.run(agents)
    final = env.steps[-1]
    rewards = [state.reward for state in final]
    statuses = [state.status for state in final]
    winner_slot = None
    if rewards and max(rewards) > min(rewards):
        winner_slot = rewards.index(max(rewards))
    return {
        "seed": int(seed),
        "player_count": int(player_count),
        "agents": list(agents),
        "rewards": rewards,
        "statuses": statuses,
        "steps": len(env.steps),
        "winner_slot": winner_slot,
        "elapsed_seconds": time.perf_counter() - start,
    }
```

- [ ] **Step 3: Implement CLI wrapper**

Create `tools/run_match.py`:

```python
from __future__ import annotations

import argparse
import json

from src.orbitlab.tournament import run_match


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--agents", nargs="+", required=True)
    args = parser.parse_args()
    result = run_match(seed=args.seed, agents=args.agents, player_count=len(args.agents), debug=True)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test and CLI**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\integration\test_run_match.py -v
.\.venv-ow\Scripts\python tools\run_match.py --seed 42 --agents bots/starter/main.py bots/random_hold/main.py
```

Expected: test passes and CLI prints JSON with rewards `[1, -1]`.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/orbitlab/tournament.py tools/run_match.py tests/integration/test_run_match.py
git commit -m "feat: run authoritative orbit wars matches"
```

---

## Task 9: Storage And Reporting

**Files:**
- Create: `src/orbitlab/storage.py`
- Create: `src/orbitlab/reporting.py`
- Test: `tests/unit/test_storage.py`

- [ ] **Step 1: Write storage tests**

Create `tests/unit/test_storage.py`:

```python
from pathlib import Path

from src.orbitlab.storage import init_db, insert_match, read_matches


def test_match_roundtrip(tmp_path: Path):
    db_path = tmp_path / "results.sqlite"
    init_db(db_path)
    insert_match(
        db_path,
        {
            "match_id": "m1",
            "run_id": "r1",
            "seed": 42,
            "player_count": 2,
            "agents": ["a.py", "b.py"],
            "rewards": [1, -1],
            "statuses": ["DONE", "DONE"],
            "steps": 500,
            "winner_slot": 0,
            "elapsed_seconds": 0.25,
            "error_text": None,
        },
    )
    rows = read_matches(db_path)
    assert rows[0]["seed"] == 42
    assert rows[0]["rewards"] == [1, -1]
```

- [ ] **Step 2: Implement SQLite storage**

Create `src/orbitlab/storage.py` with `init_db`, `insert_match`, and `read_matches`. Use the schema from the Data Model section and JSON-encode list/dict fields.

- [ ] **Step 3: Implement summary reporting**

Create `src/orbitlab/reporting.py` with a function:

```python
def summarize_matches(matches: list[dict], focus_agent: str) -> dict:
    games = len(matches)
    wins = sum(1 for match in matches if match["winner_agent"] == focus_agent)
    crashes = sum(1 for match in matches if any(status != "DONE" for status in match["statuses"]))
    return {
        "games": games,
        "wins": wins,
        "win_rate": wins / games if games else 0.0,
        "crashes": crashes,
        "crash_rate": crashes / games if games else 0.0,
    }
```

When implementing `read_matches`, include a computed `winner_agent` by mapping `winner_slot` to the stored `agents` list.

- [ ] **Step 4: Run storage tests**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\unit\test_storage.py -v
```

Expected: storage roundtrip passes.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/orbitlab/storage.py src/orbitlab/reporting.py tests/unit/test_storage.py
git commit -m "feat: store and summarize tournament results"
```

---

## Task 10: Parallel Tournament Scheduler

**Files:**
- Create: `src/orbitlab/scheduler.py`
- Create: `tools/run_tournament.py`
- Create: `config/tournament_default.json`
- Test: `tests/integration/test_tournament_smoke.py`

- [ ] **Step 1: Create default tournament config**

Create `config/tournament_default.json`:

```json
{
  "label": "starter_vs_hold_smoke",
  "seeds": [1, 2, 3, 4, 5],
  "workers": 2,
  "matchups": [
    {
      "name": "starter_vs_hold",
      "agents": ["bots/starter/main.py", "bots/random_hold/main.py"],
      "player_count": 2,
      "rotate_slots": true
    }
  ]
}
```

- [ ] **Step 2: Implement scheduler**

Create `src/orbitlab/scheduler.py`. Use `multiprocessing.Pool` to run one match per worker. For `rotate_slots=true` in 2P, schedule both `[A, B]` and `[B, A]` for each seed. For 4P, schedule rotations where the focus bot appears in slots 0, 1, 2, and 3. Catch exceptions and convert them into match rows with `statuses=["ERROR"]` and `error_text` set to the exception string.

- [ ] **Step 3: Implement tournament CLI**

Create `tools/run_tournament.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.orbitlab.scheduler import run_tournament_from_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    config_path = Path(args.config)
    config = json.loads(config_path.read_text())
    run_dir = run_tournament_from_config(config, out_dir=args.out)
    print(run_dir)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add integration test**

Add to `tests/integration/test_tournament_smoke.py`:

```python
import json
from pathlib import Path

from src.orbitlab.scheduler import run_tournament_from_config


def test_scheduler_runs_rotated_smoke_tournament(tmp_path: Path):
    config = {
        "label": "pytest_smoke",
        "seeds": [1],
        "workers": 1,
        "matchups": [
            {
                "name": "starter_vs_hold",
                "agents": ["bots/starter/main.py", "bots/random_hold/main.py"],
                "player_count": 2,
                "rotate_slots": True,
            }
        ],
    }
    run_dir = Path(run_tournament_from_config(config, out_dir=tmp_path))
    summary = run_dir / "summary.csv"
    assert summary.exists()
    assert "starter_vs_hold" in summary.read_text()
```

- [ ] **Step 5: Run tournament smoke**

Run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\integration\test_tournament_smoke.py -v
.\.venv-ow\Scripts\python tools\run_tournament.py --config config\tournament_default.json
```

Expected: test passes and CLI prints a `runs/...` directory path.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src/orbitlab/scheduler.py tools/run_tournament.py config/tournament_default.json tests/integration/test_tournament_smoke.py
git commit -m "feat: run parallel rotated orbit wars tournaments"
```

---

## Task 11: Issue Detection System

**Files:**
- Create: `src/orbitlab/issues.py`
- Create: `src/orbitlab/detectors.py`
- Create: `docs/operations/issue-taxonomy.md`
- Create: `tools/analyze_run.py`

- [ ] **Step 1: Define issue records**

Create `src/orbitlab/issues.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Issue:
    detector: str
    severity: str
    message: str
    match_id: str
    step: int | None = None
    slot: int | None = None
    evidence: dict[str, Any] | None = None
```

- [ ] **Step 2: Implement first detectors**

Create `src/orbitlab/detectors.py` with these functions:

```python
def detect_crashes(match: dict) -> list[Issue]:
    ...

def detect_slot_bias(matches: list[dict], focus_agent: str, min_games_per_slot: int = 20) -> list[Issue]:
    ...

def detect_low_expansion(turn_metrics: list[dict], focus_slot: int) -> list[Issue]:
    ...

def detect_timeout_or_slow_match(match: dict, max_elapsed_seconds: float) -> list[Issue]:
    ...
```

Acceptance behavior:

- `detect_crashes` emits `P0` if any final status is not `DONE`.
- `detect_slot_bias` emits `P3` if win rate differs by more than 15 percentage points between slots after enough games.
- `detect_low_expansion` emits `P2` if the bot still owns one planet after step 60 in a match it later loses.
- `detect_timeout_or_slow_match` emits `P1` if elapsed wall time exceeds the configured threshold without a crash.

- [ ] **Step 3: Document the issue taxonomy**

Create `docs/operations/issue-taxonomy.md` with these categories:

```markdown
# Orbit Wars Issue Taxonomy

## P0 Technical Failure
- Import error
- Exception during `agent`
- Timeout
- Invalid action shape
- Non-deterministic crash on repeated seed

## P1 Likely Loss Cause
- Repeated fleets destroyed by sun
- High-production owned planet captured without reinforcement attempt
- Overlaunch leaves source planet instantly captured
- Endgame ships idle while enemy planets are reachable

## P2 Strategic Weakness
- Slow neutral expansion
- Over-defense with unused surplus
- Chasing low-value comets too often
- Attacking strongest 4P enemy while weakest enemy is exposed

## P3 Investigation Signal
- Player-slot bias
- Seed-cluster weakness
- Win-rate drop against one reference bot
- Match-length anomaly
```

- [ ] **Step 4: Build run analyzer CLI**

Create `tools/analyze_run.py` to load `matches.csv` and `turn_metrics.csv`, run all detectors, write `issues.csv`, and write `issue_report.md` grouped by severity.

- [ ] **Step 5: Run detector tests**

Create focused unit tests for `detect_crashes` and `detect_slot_bias`, then run:

```powershell
.\.venv-ow\Scripts\python -m pytest tests\unit -v
```

Expected: all unit tests pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src/orbitlab/issues.py src/orbitlab/detectors.py docs/operations/issue-taxonomy.md tools/analyze_run.py tests/unit
git commit -m "feat: classify orbit wars tournament flaws"
```

---

## Task 12: Parameter Sweep System

**Files:**
- Create: `config/sweep_default.json`
- Create: `tools/sweep_params.py`
- Modify: `src/orbitlab/scheduler.py`

- [ ] **Step 1: Define sweep config**

Create `config/sweep_default.json`:

```json
{
  "base_bot": "bots/our_v1/main.py",
  "variant_dir": "bots/generated",
  "parameters": {
    "HOSTILE_TARGET_VALUE_MULT": [1.8, 2.05, 2.3],
    "PROACTIVE_DEFENSE_RATIO": [0.18, 0.28, 0.38],
    "SIM_HORIZON": [90, 110, 130]
  },
  "opponents": [
    "bots/starter/main.py"
  ],
  "seeds": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "workers": 4
}
```

- [ ] **Step 2: Implement variant generator**

Create `tools/sweep_params.py` that:

- Reads the base bot as text.
- Generates one bot file per parameter combination.
- Prepends a comment with the variant ID and parameter values.
- Replaces exact constant assignments such as `HOSTILE_TARGET_VALUE_MULT = 2.05`.
- Writes a tournament config that tests all generated variants against configured opponents.
- Runs the tournament through `run_tournament_from_config`.

- [ ] **Step 3: Add guardrails**

If a requested constant assignment is not found exactly once in the base bot, stop with an error explaining which constant failed. This prevents silent bad sweeps.

- [ ] **Step 4: Run a tiny sweep**

Run:

```powershell
.\.venv-ow\Scripts\python tools\sweep_params.py --config config\sweep_default.json --dry-run
```

Expected: generated config is printed and no bot files are overwritten.

Then run:

```powershell
.\.venv-ow\Scripts\python tools\sweep_params.py --config config\sweep_default.json --limit 2
```

Expected: two generated variants run against the starter bot.

- [ ] **Step 5: Commit**

Run:

```powershell
git add config/sweep_default.json tools/sweep_params.py src/orbitlab/scheduler.py
git commit -m "feat: add orbit wars parameter sweep runner"
```

---

## Task 13: Replay And Leaderboard Diagnostics

**Files:**
- Create: `tools/fetch_episodes.py`
- Create: `tools/analyze_replay.py`
- Create: `docs/operations/daily-submission-checklist.md`

- [ ] **Step 1: Create episode fetcher**

Create `tools/fetch_episodes.py` that shells out through `.\kaggle.ps1` for:

```powershell
.\kaggle.ps1 competitions episodes <SUBMISSION_ID> -v
.\kaggle.ps1 competitions replay <EPISODE_ID> -p runs\leaderboard\<SUBMISSION_ID>\replays
.\kaggle.ps1 competitions logs <EPISODE_ID> <AGENT_INDEX> -p runs\leaderboard\<SUBMISSION_ID>\logs
```

The script must never print access tokens. It only prints submission IDs, episode IDs, file paths, and command exit codes.

- [ ] **Step 2: Create replay analyzer**

Create `tools/analyze_replay.py` that reads replay JSON, converts observations into `ObservationState`, extracts per-turn metrics, and runs the same detectors from `src/orbitlab/detectors.py`.

- [ ] **Step 3: Create daily submission checklist**

Create `docs/operations/daily-submission-checklist.md`:

```markdown
# Daily Orbit Wars Submission Checklist

1. Candidate has a unique version name.
2. Candidate imports locally with Python 3.11.
3. Candidate completes 100 starter smoke games with zero P0 issues.
4. Candidate beats previous internal champion over 400 rotated 2P games.
5. Candidate beats or ties previous internal champion over 400 rotated 4P games.
6. Candidate does not increase P1 issue rate by more than 5%.
7. Submission message states the one hypothesis being tested.
8. After leaderboard games appear, fetch episodes and classify losses.
```

- [ ] **Step 4: Run fetcher help**

Run:

```powershell
.\.venv-ow\Scripts\python tools\fetch_episodes.py --help
.\.venv-ow\Scripts\python tools\analyze_replay.py --help
```

Expected: both commands show usage and do not require credentials for help output.

- [ ] **Step 5: Commit**

Run:

```powershell
git add tools/fetch_episodes.py tools/analyze_replay.py docs/operations/daily-submission-checklist.md
git commit -m "feat: add leaderboard episode diagnostics"
```

---

## Task 14: Submission Packaging

**Files:**
- Create: `tools/submit_candidate.py`
- Create: `submissions/.gitkeep`

- [ ] **Step 1: Implement package validation**

Create `tools/submit_candidate.py` that:

- Requires `--bot bots/<name>/main.py`.
- Imports the bot in a subprocess.
- Runs a 10-seed smoke tournament against `bots/starter/main.py`.
- Copies the bot to `submissions/<version>/main.py`.
- Prints the exact Kaggle submit command.
- Executes submit only when `--execute` is supplied.

Submit command shape:

```powershell
.\kaggle.ps1 competitions submit orbit-wars -f submissions\<version>\main.py -m "<message>"
```

- [ ] **Step 2: Test dry-run packaging**

Run:

```powershell
.\.venv-ow\Scripts\python tools\submit_candidate.py --bot bots\starter\main.py --version starter_dry_run --message "starter dry run"
```

Expected: creates `submissions/starter_dry_run/main.py`, runs smoke games, prints the submit command, and does not submit.

- [ ] **Step 3: Commit**

Run:

```powershell
git add tools/submit_candidate.py submissions
git commit -m "feat: package orbit wars submission candidates"
```

---

## Full-Mechanics Mirror Completion Checklist

The mirror simulator is complete only when these tests exist and pass:

- Fleet speed matches the official logarithmic curve for ships `1`, `10`, `100`, `500`, and `1000`.
- Launch points spawn outside the source planet radius by `0.1`.
- Owned planets produce after fleet launches.
- Neutral planets do not produce.
- Orbiting planets rotate using current position and `angular_velocity`.
- Static planets do not rotate.
- Fleets crossing the sun are removed.
- Fleets leaving the board are removed.
- Fleet segments collide with planets continuously, not only at endpoints.
- Moving planets sweep fleets into combat after rotation.
- Multiple fleets arriving on one planet resolve as one grouped combat event.
- Same-owner attacking fleets are summed before combat.
- Top-two attackers duel before fighting garrison.
- Tied top attackers vanish.
- Friendly survivor reinforces.
- Enemy survivor captures with surplus.
- Comets appear as planets, can be captured, produce while owned, move by path, and expire with their ships.
- A fleet launched from a departing comet is not allowed because comet expiration happens before launch.
- Two-player and four-player games both run under the scheduler.
- Slot rotation schedules each bot in every slot.

Each item gets one test. If a test fails, fix the mirror or document the verified official behavior if the README is incomplete.

---

## Flaw Detection Roadmap

Build detectors in this order:

1. **P0 Technical Detector:** crashes, timeouts, invalid action shape, import failure.
2. **Sun Death Detector:** counts fleets removed by sun collision when replay data exposes removals or mirror predicts them from actions.
3. **Slow Expansion Detector:** flags one-planet state after step 60 in losses.
4. **Overlaunch Detector:** flags source planets emptied below predicted incoming threat.
5. **Defense Miss Detector:** flags owned planet loss where reinforcement was possible within travel time.
6. **Idle Surplus Detector:** flags owned planets with large ship surplus and reachable profitable targets.
7. **Bad Comet Chase Detector:** flags fleets sent to comets that expire before arrival or produce low return.
8. **Weak Enemy Ignored Detector:** in 4P, flags repeated attacks on strong enemy while weakest enemy owned exposed high-production planets.
9. **Endgame Waste Detector:** flags ships idle on planets when remaining turns still allow arrival at enemy planets.
10. **Slot Bias Detector:** flags large win-rate gap by player slot.
11. **Regression Detector:** compares issue rates between current candidate and prior champion.

Detector output must include:

- `detector`
- `severity`
- `match_id`
- `step`
- `slot`
- `message`
- `evidence_json`

Example issue:

```json
{
  "detector": "slow_expansion",
  "severity": "P2",
  "match_id": "our_v1__starter__seed_77__slot_0",
  "step": 60,
  "slot": 0,
  "message": "Bot still owned one planet at step 60 and later lost.",
  "evidence_json": {
    "owned_planets": 1,
    "final_reward": -1,
    "nearest_neutral_ships": 7
  }
}
```

---

## Parallel Testing Strategy

Default worker count:

- Start with `workers = max(1, cpu_count() - 1)`.
- Use `workers = 1` when debugging crashes because logs are easier to read.
- Use `workers = 4` for normal sweeps unless CPU saturation causes timeouts.

Isolation rules:

- One official Kaggle environment per worker process.
- One match per task.
- Never reuse an environment between matches.
- Bot files are treated as immutable during a run.
- Every generated variant has a unique directory and hash.

Scheduling rules:

- For 2P, every seed schedules `[A, B]` and `[B, A]`.
- For 4P, every seed schedules rotations where the focus bot appears in all four slots.
- For public-agent gauntlets, pair the candidate with three fixed opponents and rotate candidate slot.
- For internal regression, test candidate against the last accepted internal champion.

Run sizes:

- Smoke: 10 games, used after code changes.
- Local confidence: 200 rotated games.
- Candidate gate: 800 rotated games: 400 2P plus 400 4P.
- Sweep gate: 50-100 games per variant for early elimination, then 400 for finalists.
- Submission gate: 1,000 total games with zero P0 issues.

---

## Operating Rhythm For The Month

Daily cadence:

1. Run smoke tests.
2. Run local gauntlet for the current champion.
3. Review `P0` and `P1` issues first.
4. Fix one flaw category at a time.
5. Run regression tournament.
6. Submit only if candidate beats the prior champion and has a clear leaderboard hypothesis.
7. Fetch leaderboard episodes when available.
8. Convert losses into issue categories.

Weekly review:

- Week 1 review: runner reliability, result storage, basic summaries.
- Week 2 review: mirror simulator agreement with official behavior on targeted mechanics.
- Week 3 review: detector usefulness and parameter sweep throughput.
- Week 4 review: leaderboard feedback, submission discipline, and final bot stabilization.

Stop conditions:

- If P0 rate is above zero, do not submit except for a deliberate debug submission.
- If candidate loses to prior champion locally by more than 2 percentage points over 400 games, do not submit.
- If detector reports a new P1 category introduced by the candidate, fix or revert before submitting.
- If leaderboard results contradict local results twice in a row, add the leaderboard opponent pattern to the local gauntlet before making another major change.

---

## Self-Review

Spec coverage:

- Full official mechanics are covered by the mirror checklist.
- Parallel execution is covered by Task 10 and the Parallel Testing Strategy.
- Flaw detection is covered by Task 11 and the Flaw Detection Roadmap.
- Month-long execution is covered by the Week 1-4 plan and Operating Rhythm.
- Kaggle submission and episode diagnostics are covered by Tasks 13 and 14.

Placeholder scan:

- This plan contains no `TBD`, no `TODO`, and no unspecified implementation slots.
- Each implementation task names concrete files, commands, and expected outcomes.

Type consistency:

- State types are defined in `src/orbitlab/game_types.py`.
- Adapters return `ObservationState`.
- Validators consume `Move` and `PlanetState`.
- Mirror simulator consumes `ObservationState` and `dict[int, list[Move]]`.
- Tournament runner returns plain dictionaries for storage and reporting.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-11-orbit-wars-simulator-lab.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - Dispatch a fresh worker per task, review between tasks, and keep parallel progress fast once write scopes are separated.
2. **Inline Execution** - Execute tasks in this session using batch checkpoints.

For this month-long lab, use Subagent-Driven for Tasks 1-6 once the first skeleton lands, then use Inline Execution for submission-sensitive tooling where credentials and local state matter.

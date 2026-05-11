# Orbit Wars High-End Simulator Analytics System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the missing high-end simulator, replay analytics, bot comparison, and visual review system needed to find actual Orbit Wars bot flaws rather than only watching pretty replays.

**Architecture:** Keep the official Kaggle environment as the source of truth for match outcomes, then layer trace export, replay analysis, mirror parity tests, tactical detectors, run comparison, and a cleaner viewer on top. The viewer theme stays cherry red/light red/black/white, but the analysis stack is neutral, testable Python that can feed CLI reports, CSVs, and browser panels.

**Tech Stack:** Python 3.11, `kaggle-environments`, pytest, SQLite/CSV/JSON, static HTML/CSS/JavaScript Canvas 2D, GitHub Actions, local static HTTP server for browser verification.

---

## Page 1: What Was Missing And What Must Change

The existing project already has a good foundation: official match runner, basic tournament scheduler, a diagnostic mirror simulator, SQLite/CSV outputs, simple detectors, run summaries, replay export, and a working visual viewer. The problem is that those pieces are still too shallow for serious competition work. The viewer looks good, but it does not yet think. The simulator mirror exists, but it is not yet continuously checked against official replay traces. The analytics report win rate, but they do not yet explain the loss. The comparison tool can compare run summaries, but it does not yet make candidate-vs-baseline testing the default workflow.

This plan fixes those gaps by building the missing layers in order:

1. Replay-level flaw detection.
2. Issue-enriched viewer JSON.
3. Cleaner viewer side panels with real analytical data.
4. Bot comparison command that runs candidate-vs-baseline gauntlets.
5. Mirror parity harness against official traces.
6. Tactical mistake detectors.
7. Comet and sun-risk analysis.
8. Report generation that turns flaws into next bot tasks.
9. Viewer usability pass.
10. Verification and daily operating loop.

The red theme applies only to the UI. Python reports, plans, data artifacts, and CLI output should stay clean and practical.

### Task 1: Establish The Missing-System Contract

**Files:**
- Create: `docs/superpowers/plans/2026-05-11-orbit-wars-high-end-sim-analytics-system.md`
- Modify: `README.md`

- [ ] **Step 1: Document skipped or incomplete parts**

Write a section that names every missing piece:

```markdown
## Missing Pieces

- Replay flaw detection only catches crashes and slow matches.
- Viewer side panel does not rank likely causes of bad play.
- Bot comparison is run-summary based, not candidate workflow based.
- Mirror simulator is not yet parity-checked against official traces.
- Comet timing, sun deaths, bad launch lanes, idle overstock, and lost fleets are not automatically flagged.
```

- [ ] **Step 2: Add README link**

Add:

```markdown
The high-end analytics roadmap is in `docs/superpowers/plans/2026-05-11-orbit-wars-high-end-sim-analytics-system.md`.
```

- [ ] **Step 3: Commit planning doc**

Run:

```powershell
git add README.md docs/superpowers/plans/2026-05-11-orbit-wars-high-end-sim-analytics-system.md
git commit -m "docs: plan high-end orbit wars analytics system"
```

Expected: one docs commit.

---

## Page 2: Replay-Level Flaw Detection

Replay-level detectors must inspect frames, actions, fleet disappearance, planet ownership changes, comet windows, and per-slot metrics. This is separate from match-level detectors because match-level records only know final status and elapsed time.

### Task 2: Add `src/orbitlab/replay_analysis.py`

**Files:**
- Create: `src/orbitlab/replay_analysis.py`
- Create: `tests/unit/test_replay_analysis.py`
- Modify: `src/orbitlab/replay.py`

- [ ] **Step 1: Write failing tests for bad launch, sun death, missed comet, slow expansion, and idle overstock**

Create `tests/unit/test_replay_analysis.py`:

```python
from src.orbitlab.replay_analysis import analyze_replay_payload


def test_flags_bad_launch_lane_through_sun():
    replay = {
        "match_id": "m1",
        "player_count": 2,
        "frames": [
            {
                "step": 0,
                "planets": [[0, 0, 25.0, 50.0, 2.0, 30.0, 3]],
                "fleets": [],
                "comet_planet_ids": [],
                "actions": [[[0, 0.0, 10]], []],
                "metrics": [],
            }
        ],
    }
    issues = analyze_replay_payload(replay)
    assert any(issue.detector == "bad_launch_sun_lane" for issue in issues)
```

Also add tests for:

```python
assert any(issue.detector == "sun_death" for issue in issues)
assert any(issue.detector == "missed_comet_window" for issue in issues)
assert any(issue.detector == "slow_expansion" for issue in issues)
assert any(issue.detector == "idle_overstock" for issue in issues)
```

- [ ] **Step 2: Run tests red**

Run:

```powershell
.venv-ow\Scripts\python -m pytest tests\unit\test_replay_analysis.py -q
```

Expected: import failure for `src.orbitlab.replay_analysis`.

- [ ] **Step 3: Implement detector helpers**

Create functions:

```python
def analyze_replay_payload(replay: dict) -> list[Issue]: ...
def detect_bad_launches(replay: dict) -> list[Issue]: ...
def detect_sun_deaths(replay: dict) -> list[Issue]: ...
def detect_missed_comets(replay: dict) -> list[Issue]: ...
def detect_replay_slow_expansion(replay: dict) -> list[Issue]: ...
def detect_idle_overstock(replay: dict) -> list[Issue]: ...
```

Use existing helpers:

```python
from .collision import is_out_of_bounds, segment_hits_sun
from .physics import BOARD_SIZE, fleet_speed, launch_point
```

- [ ] **Step 4: Run tests green**

Run:

```powershell
.venv-ow\Scripts\python -m pytest tests\unit\test_replay_analysis.py -q
```

Expected: all replay analysis tests pass.

- [ ] **Step 5: Integrate with replay export**

In `src/orbitlab/replay.py`, after creating the replay payload, call:

```python
from .replay_analysis import analyze_replay_payload

auto_issues = analyze_replay_payload(payload)
payload["issues"] = [_issue_row(issue) for issue in list(issues or []) + auto_issues]
```

Expected: viewer JSON contains automatic flaw issues even when match-level issues are empty.

---

## Page 3: Issue Evidence Quality

Flaw flags are only useful if they explain what happened. Each issue must include enough evidence to inspect the exact turn and reproduce the reasoning.

### Task 3: Standardize Replay Issue Evidence

**Files:**
- Modify: `src/orbitlab/replay_analysis.py`
- Modify: `tests/unit/test_replay_analysis.py`
- Modify: `docs/operations/issue-taxonomy.md`

- [ ] **Step 1: Add evidence assertions**

Add tests:

```python
issue = next(issue for issue in issues if issue.detector == "bad_launch_sun_lane")
assert issue.step == 0
assert issue.slot == 0
assert issue.evidence["planet_id"] == 0
assert issue.evidence["ships"] == 10
```

- [ ] **Step 2: Store evidence for each detector**

Bad launch:

```python
{"planet_id": 0, "angle": 0.0, "ships": 10, "source": [25.0, 50.0]}
```

Sun death:

```python
{"fleet_id": 7, "ships": 12, "from": [39.0, 50.0], "predicted_to": [42.2, 50.0]}
```

Missed comet:

```python
{"comet_id": 4, "nearest_planet_id": 0, "distance": 20.0, "available_ships": 40.0}
```

Slow expansion:

```python
{"planets": 1, "threshold_step": 60}
```

Idle overstock:

```python
{"planet_id": 0, "ships": 85.0, "production": 5, "idle_frames": 8}
```

- [ ] **Step 3: Update taxonomy**

Add detector definitions and severity:

```markdown
| bad_launch_sun_lane | P1 | Launch ray crosses the sun danger radius. |
| sun_death | P1 | Fleet disappeared on a predicted sun-crossing segment. |
| missed_comet_window | P2 | Capturable comet opportunity was ignored. |
| idle_overstock | P2 | High-value planet hoarded ships without pressure. |
```

---

## Page 4: Cleaner Analytical Viewer

The viewer should not make the user hunt through raw numbers. It should answer: who is ahead, why, what just changed, and what looks suspicious.

### Task 4: Add Viewer Insight Panels

**Files:**
- Modify: `viewer/index.html`
- Modify: `viewer/styles.css`
- Modify: `viewer/app.js`
- Modify: `viewer/sample-viewer-replay.json`

- [ ] **Step 1: Add panels**

Insert three sections above Issues:

```html
<section class="panel-section">
  <h2>Bot Compare</h2>
  <div id="comparePanel" class="compare-panel"></div>
</section>

<section class="panel-section">
  <h2>Current Read</h2>
  <div id="insightPanel" class="insight-panel"></div>
</section>

<section class="panel-section">
  <h2>Flaw Signals</h2>
  <div id="flawSignalPanel" class="flaw-signal-panel"></div>
</section>
```

- [ ] **Step 2: Compute current frame comparison**

In `viewer/app.js`:

```javascript
function buildFrameComparison(frameData) {
  const metrics = frameData.metrics || [];
  const bestShips = Math.max(...metrics.map((m) => Number(m.total_ships || 0)));
  return metrics.map((metric) => ({
    slot: metric.slot,
    shipDelta: Number(metric.total_ships || 0) - bestShips,
    production: Number(metric.production || 0),
    planets: Number(metric.planets || 0),
    fleets: Number(metric.fleets || 0),
  }));
}
```

- [ ] **Step 3: Render insight cards**

Cards:

```text
Leader: slot with highest total ships.
Production edge: slot with highest production.
Map control: slot with most planets.
Pressure: slot with most ships in transit.
```

- [ ] **Step 4: Render flaw signals**

Filter issues within eight turns of the current frame. Use severity color and detector labels.

- [ ] **Step 5: Improve visual hierarchy**

CSS rules:

```css
.compare-panel,
.insight-panel,
.flaw-signal-panel {
  display: grid;
  gap: 8px;
}

.insight-card {
  border: 1px solid rgba(255, 111, 126, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  padding: 10px;
}
```

---

## Page 5: Bot Comparison Workflow

The project needs a direct bot compare command. The user should not manually assemble config files every time.

### Task 5: Add `tools/compare_bots.py`

**Files:**
- Create: `src/orbitlab/bot_compare.py`
- Create: `tools/compare_bots.py`
- Create: `tests/unit/test_bot_compare.py`
- Modify: `README.md`

- [ ] **Step 1: Write config builder tests**

Test:

```python
from src.orbitlab.bot_compare import build_compare_config


def test_build_compare_config_rotates_slots_and_can_export_replays():
    config = build_compare_config(
        candidate="bots/our_v1/main.py",
        baseline="bots/starter/main.py",
        seeds=[1, 2],
        workers=2,
        export_viewer_replays=True,
    )
    assert config["seeds"] == [1, 2]
    assert config["workers"] == 2
    assert config["export_viewer_replays"] is True
    assert config["matchups"][0]["agents"] == ["bots/our_v1/main.py", "bots/starter/main.py"]
    assert config["matchups"][0]["rotate_slots"] is True
```

- [ ] **Step 2: Implement builder**

Create:

```python
def build_compare_config(candidate, baseline, seeds, workers=1, export_viewer_replays=False) -> dict:
    return {
        "label": f"compare_{Path(candidate).stem}_vs_{Path(baseline).stem}",
        "seeds": list(seeds),
        "workers": workers,
        "export_viewer_replays": export_viewer_replays,
        "matchups": [{
            "name": "candidate_vs_baseline",
            "agents": [candidate, baseline],
            "player_count": 2,
            "rotate_slots": True,
        }],
    }
```

- [ ] **Step 3: Implement CLI**

`tools/compare_bots.py` should accept:

```text
--candidate
--baseline
--seeds 1 2 3
--workers
--out
--viewer-replays
```

Then call `run_tournament_from_config`, `analyze_run.main`, and print the run directory.

- [ ] **Step 4: README command**

Add:

```powershell
.venv-ow\Scripts\python tools\compare_bots.py --candidate bots/our_v1/main.py --baseline bots/starter/main.py --seeds 1 2 3 4 5 --viewer-replays
```

---

## Page 6: Mirror Simulator Accuracy

The mirror simulator cannot be trusted until it is tested against official trace transitions. The goal is not to replace Kaggle. The goal is to use the mirror for diagnosis and prediction while continuously checking it.

### Task 6: Add Official Trace Parity Harness

**Files:**
- Create: `src/orbitlab/parity.py`
- Create: `tests/integration/test_mirror_parity.py`
- Modify: `src/orbitlab/mirror.py`

- [ ] **Step 1: Write a trace extraction helper**

Expected API:

```python
def extract_observation_frames(env) -> list[dict]:
    return [{"step": i, "observation": obs_dict} for i, obs_dict in ...]
```

- [ ] **Step 2: Write parity test for no-action hold bot**

Test:

```python
def test_mirror_parity_static_production_first_steps():
    env = make("orbit_wars", configuration={"seed": 42}, debug=True)
    env.run(["bots/random_hold/main.py", "bots/random_hold/main.py"])
    frames = extract_observation_frames(env)
    report = compare_mirror_to_official(frames, max_steps=5)
    assert report["max_ship_error"] <= 0.001
```

- [ ] **Step 3: Implement comparison report**

Return:

```python
{
  "checked_steps": 5,
  "max_position_error": 0.0,
  "max_ship_error": 0.0,
  "mismatches": []
}
```

- [ ] **Step 4: Mark known gaps explicitly**

If comet spawning or simultaneous fleet collisions are not parity-checked yet, the report should name them as unchecked categories rather than pretending they are done.

---

## Page 7: High-End Tactical Mistake Detection

The system must produce bot-improvement clues, not just labels.

### Task 7: Tactical Detectors

**Files:**
- Modify: `src/orbitlab/replay_analysis.py`
- Modify: `tests/unit/test_replay_analysis.py`
- Modify: `viewer/app.js`

- [ ] **Step 1: Add lost fleet without gain**

Detector:

```text
fleet_disappeared_without_capture
```

Logic:

- A fleet exists at step `t`.
- It does not exist at `t+1`.
- No planet changed to that fleet owner within one frame.
- Segment did not hit sun.
- Fleet did not go out of bounds.

Severity: P2.

- [ ] **Step 2: Add late trailing no pressure**

Detector:

```text
late_trailing_no_pressure
```

Logic:

- Step >= 350.
- Slot trails leader by >= 25 total ships.
- Slot has <= 1 fleet and ships_in_fleets <= 5.

Severity: P2.

- [ ] **Step 3: Add overdefended low-production planet**

Detector:

```text
overdefended_low_production
```

Logic:

- Production <= 2.
- Ships >= 65.
- Slot has fewer planets than opponent.

Severity: P3.

- [ ] **Step 4: Viewer phrasing**

Map detector names to plain labels:

```javascript
const detectorLabels = {
  bad_launch_sun_lane: "Bad launch lane",
  sun_death: "Fleet crossed sun",
  missed_comet_window: "Missed comet window",
  slow_expansion: "Slow expansion",
  idle_overstock: "Idle overstock",
};
```

---

## Page 8: Analytical Data On The Side

The side panel needs to show derived data, not only raw telemetry.

### Task 8: Side Analytics Metrics

**Files:**
- Modify: `src/orbitlab/replay.py`
- Modify: `src/orbitlab/replay_analysis.py`
- Modify: `viewer/app.js`

- [ ] **Step 1: Add per-frame derived metrics**

Each frame should expose:

```json
"derived": {
  "leader_slot": 0,
  "ship_spread": 24.0,
  "production_leader_slot": 1,
  "planet_leader_slot": 0,
  "pressure_leader_slot": 0
}
```

- [ ] **Step 2: Add timeline issue density**

Replay payload:

```json
"analysis": {
  "issue_counts_by_step": {"60": 2},
  "severity_counts": {"P1": 1, "P2": 3},
  "detector_counts": {"slow_expansion": 1}
}
```

- [ ] **Step 3: Render side data**

Viewer should show:

- Current leader.
- Current production edge.
- Current pressure edge.
- Ship spread.
- Nearby flaw count.
- Total issue count by severity.

---

## Page 9: Viewer UX And Accuracy Pass

The viewer must be cleaner and more intuitive. It should not look like a spreadsheet glued to a canvas.

### Task 9: UX Cleanup

**Files:**
- Modify: `viewer/index.html`
- Modify: `viewer/styles.css`
- Modify: `viewer/app.js`

- [ ] **Step 1: Group controls by intent**

Header:

```text
Load | Sample | Fit
```

Timeline:

```text
Prev | Play/Pause | Next | slider | speed | Jump issue
```

Side:

```text
Bot Compare
Current Read
Flaw Signals
Telemetry
Notes
```

- [ ] **Step 2: Reduce visual noise**

Keep glow on:

- Sun danger zone.
- Fleets.
- Active issue highlight.

Do not glow every panel equally.

- [ ] **Step 3: Add clickable timeline issue markers**

Represent issues as small red ticks over the slider using a positioned overlay:

```html
<div id="timelineMarkers" class="timeline-markers"></div>
```

- [ ] **Step 4: Browser QA**

Open:

```text
http://127.0.0.1:8765/viewer/index.html?replay=/runs/manual_viewer.json
```

Verify:

- Canvas nonblank.
- Side panels fit without text overlap.
- Issue jump moves to a flagged turn.
- Notes still add.
- Console has no errors.

---

## Page 10: Completion Criteria And Daily Loop

The work is not complete because code exists. It is complete when the lab can run a candidate-vs-baseline comparison, export replays, flag likely mistakes, and show those mistakes in the viewer.

### Task 10: Verification, Commit, Push, And Operating Loop

**Files:**
- Modify: `docs/operations/daily-submission-checklist.md`
- Modify: `docs/operations/visual-review-loop.md`
- Modify: `README.md`

- [ ] **Step 1: Full tests**

Run:

```powershell
.venv-ow\Scripts\python -m pytest tests -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 2: Real match replay**

Run:

```powershell
.venv-ow\Scripts\python tools\run_match.py --seed 42 --agents bots/starter/main.py bots/random_hold/main.py --matchup starter_vs_hold --replay-out runs/manual_viewer.json
```

Expected:

```text
"statuses": ["DONE", "DONE"]
"replay_path": "runs\\manual_viewer.json"
```

- [ ] **Step 3: Compare bots smoke**

Run:

```powershell
.venv-ow\Scripts\python tools\compare_bots.py --candidate bots/our_v1/main.py --baseline bots/starter/main.py --seeds 1 2 --viewer-replays
```

Expected: run directory with `leaderboard.csv`, `matchup_matrix.csv`, `phase_metrics.csv`, and `replays/*.viewer.json`.

- [ ] **Step 4: Browser verification**

Use the in-app browser. Check:

```text
loaded real replay
timeline advances
flaw signals visible
bot compare visible
no browser console errors
```

- [ ] **Step 5: Commit and push**

Run:

```powershell
git add .
git commit -m "feat: add replay flaw analytics and bot comparison workflow"
git push
```

Expected: GitHub main updated.

## Final Acceptance Checklist

- [ ] Automatic replay issue detectors include bad launches, sun deaths, missed comets, slow expansion, and idle overstock.
- [ ] Viewer side panel shows bot comparison and current analytical read.
- [ ] Bot compare CLI runs candidate-vs-baseline tournaments without hand-written config.
- [ ] Replay JSON carries issue counts and derived frame metrics.
- [ ] Mirror parity work is documented and first parity test exists.
- [ ] Daily loop tells us how to convert repeated observations into detector or bot changes.
- [ ] Tests pass.
- [ ] Browser QA passes.
- [ ] Work is committed and pushed.

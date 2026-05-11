# Orbit Wars Visual Simulator Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an advanced visual layer that lets us watch Orbit Wars simulations with synchronized map playback, per-turn analytics, issue markers, and observational notes that feed back into bot improvement.

**Architecture:** Keep the tournament runner authoritative and export replay-ready JSON artifacts from finished matches. Build a static browser viewer under `viewer/` that loads those artifacts locally, renders the board on canvas, displays metrics and notes beside the map, and can be verified without a backend server. The visual direction is sleek cherry red, light red, black, and white with restrained glow effects that make fleet motion, sun danger, and ownership pressure legible.

**Tech Stack:** Python 3.11 for replay export and artifact generation, standard-library JSON/CSV, static HTML/CSS/JavaScript, Canvas 2D, pytest for exporter tests, and browser verification for the viewer.

---

## Why This Layer Matters

The simulator lab already gives us match outcomes, metrics, and issue CSVs. That is necessary but not enough for top-10 work because many Orbit Wars errors are visual and temporal. A bot can lose not because a single scalar metric is bad, but because it expands along the wrong orbital lane, launches through the sun, misses a moving planet by one turn, over-defends a low-production planet, ignores a comet timing window, or sends a fleet that arrives after the planet has rotated away from the assumed intercept.

The visual layer is the bridge between raw tournament evidence and strategic insight. It should make the match legible at three speeds:

- Frame-by-frame debugging, where we inspect one launch, one collision, or one comet capture.
- Normal playback, where we watch expansion tempo, pressure, defense, and map control evolve.
- Fast review, where issue markers and notes jump us to the turns that probably matter.

This is not a decorative UI. It is an analysis tool. The first version should prioritize correctness, clarity, and fast iteration over fancy animation. Once the data contract is stable, we can make it prettier and more interactive.

## Success Criteria

The viewer is useful when it can answer these questions quickly:

- What did every planet, fleet, and comet look like at a given turn?
- Which player owned each planet and how many ships were stationed there?
- Which fleets were in transit, how many ships were in them, and where did they appear to be heading?
- How did each player compare on planets, production, ships on planets, ships in fleets, and fleet count over time?
- Which turns have detector issues, crashes, slowdowns, suspicious fleet loss, slot bias signals, or expansion weakness?
- What observation notes did we record during review, and which turn/agent/issue do they refer to?
- Can we load a replay artifact directly from a run directory without starting a service?

The viewer should be considered ready for daily use when a local match can be generated with one command, opened in the browser, scrubbed through with a timeline, and reviewed with visible analytics in under one minute.

## Data Contract

Replay JSON should be generated from the official Kaggle environment after a match. The exporter should not guess game state from metrics alone. It should capture the observations already produced by the environment.

Target artifact:

```text
runs/<run_id>/replays/<match_id>.viewer.json
```

Top-level shape:

```json
{
  "schema_version": 1,
  "game": "orbit_wars",
  "match_id": "starter_vs_hold__seed_42__rot_0",
  "run_id": "20260511_170000_smoke",
  "seed": 42,
  "player_count": 2,
  "agents": ["bots/starter/main.py", "bots/random_hold/main.py"],
  "rewards": [1, -1],
  "statuses": ["DONE", "DONE"],
  "winner_slot": 0,
  "board": {
    "size": 100,
    "center": [50, 50],
    "sun_radius": 10
  },
  "frames": [
    {
      "step": 0,
      "planets": [[0, 0, 20.0, 20.0, 2.0, 10.0, 3]],
      "fleets": [],
      "comets": [],
      "comet_planet_ids": [],
      "metrics": [
        {
          "slot": 0,
          "planets": 1,
          "ships_on_planets": 10.0,
          "ships_in_fleets": 0.0,
          "production": 3,
          "fleets": 0
        }
      ],
      "actions": []
    }
  ],
  "issues": [],
  "notes": []
}
```

The first exporter version can leave `actions` empty if the official environment does not expose clean per-turn actions in a stable format. Map playback and metrics are the first priority. Actions can be added after we inspect environment traces more deeply.

## Visual Layout

The first screen should be the tool, not a landing page.

Left side:

- Full board canvas with a fixed 100x100 coordinate system.
- Sun in the center with a clear danger radius.
- Planets rendered by owner color, radius, production ring, and ship label.
- Fleets rendered as directional particles or short arrows, colored by owner.
- Comets rendered with a distinct outline and optional path hint.

Bottom:

- Step timeline slider with play/pause, speed control, step forward/back, and jump-to-issue controls.
- Current step, total steps, seed, matchup, and winner/status summary.

Right side:

- Player comparison table for planets, production, total ships, ships in fleets, and fleet count.
- Phase label: early, mid, late.
- Issue list filtered to current turn or nearby turns.
- Notes panel with a text area, add-note button, and exported notes JSON.

Top or compact header:

- Load replay JSON file.
- Load bundled sample if present.
- Toggle labels, fleet trails, comet paths, and notes.

## Rendering Rules

Rendering should be deterministic and readable:

- Board coordinates map linearly to canvas coordinates.
- The board should preserve aspect ratio and avoid stretching.
- Planet labels should never resize the board or move elements.
- Owner colors must be distinct, colorblind-conscious enough for quick review, and repeated consistently across map and metrics.
- Neutral planets need a separate muted color.
- The sun must remain visible even when many fleets cross the center.
- Current issue turns should create visible but restrained highlights.
- The viewer should avoid giant marketing sections, decorative cards, and unrelated text.

## Observational Notes

Notes are not just UI comments. They are how we convert a review into bot work.

Each note should contain:

- `step`: current step when the note is created.
- `agent` or `slot`: optional focus.
- `category`: expansion, defense, comet, collision, timing, crash, timeout, scoring, or other.
- `text`: human note.
- `created_at`: local ISO timestamp.

First version can store notes in browser memory and allow JSON export by copying/downloading from the page. Later versions can write notes back into run artifacts through a small local helper or a CLI merge command.

Notes should be encouraged by workflow:

- Jump to issue.
- Watch 10-20 turns before it.
- Add observation.
- Convert repeated observations into a detector or bot change.

## Step-By-Step Integration

### Phase 1: Replay Export

- [ ] Add tests for replay frame export using fake environment steps.
- [ ] Create `src/orbitlab/replay.py`.
- [ ] Export board constants, frames, metrics, issues, and match metadata.
- [ ] Add `--replay-out` to `tools/run_match.py`.
- [ ] Add optional replay export paths to tournament results later, once the single-match path is stable.

### Phase 2: Static Viewer

- [ ] Create `viewer/index.html`, `viewer/styles.css`, and `viewer/app.js`.
- [ ] Load a replay JSON file from a file input.
- [ ] Render the board canvas.
- [ ] Implement step slider, play/pause, and speed.
- [ ] Render current metrics and issue list.
- [ ] Add notes panel and in-memory note list.

### Phase 3: Sample Artifact

- [ ] Create a tiny checked-in sample replay under `viewer/sample-viewer-replay.json`.
- [ ] Add a sample button so the viewer opens immediately without requiring a run.
- [ ] Keep sample data small enough for GitHub review.

### Phase 4: Analysis Feedback Loop

- [ ] Add issue markers to the timeline.
- [ ] Add phase labels using the same phase logic as `src/orbitlab/analytics.py`.
- [ ] Add run comparison notes: what changed from previous bot to current bot.
- [ ] Add exportable notes JSON.

### Phase 5: Verification

- [ ] Add Python tests for replay export.
- [ ] Run a real match and export viewer JSON.
- [ ] Open `viewer/index.html` in Chrome.
- [ ] Verify map is nonblank, timeline moves, metrics update, notes can be added, and sample replay loads.
- [ ] Capture any visual defects as issues, not vague impressions.

## File Structure

Create or modify:

```text
src/orbitlab/replay.py
tests/unit/test_replay.py
tools/run_match.py
viewer/index.html
viewer/styles.css
viewer/app.js
viewer/sample-viewer-replay.json
docs/operations/visual-review-loop.md
docs/superpowers/plans/2026-05-11-orbit-wars-simulator-lab.md
```

Responsibilities:

- `src/orbitlab/replay.py`: converts official environment state into viewer JSON.
- `tests/unit/test_replay.py`: validates replay schema, frame count, metrics, and note/issue passthrough.
- `tools/run_match.py`: writes viewer JSON when `--replay-out` is provided.
- `viewer/index.html`: static viewer shell and controls.
- `viewer/styles.css`: responsive tool layout.
- `viewer/app.js`: file loading, rendering, timeline, metrics, notes, and sample replay loading.
- `viewer/sample-viewer-replay.json`: small deterministic sample artifact.
- `docs/operations/visual-review-loop.md`: daily operating method for turning watched simulations into bot changes.

## Risk Controls

Do not let the viewer become a second simulator. It should visualize exported authoritative state. Any prediction overlays must be clearly marked as projections and should come from named helper functions.

Do not block tournament work on visual polish. The first viewer must be correct enough to support review, then we iterate.

Do not store large replay dumps in git. Checked-in sample data should be tiny. Full run replay artifacts stay under ignored `runs/`.

Do not let notes become private memory. Anything important should be turned into a detector, issue taxonomy entry, or bot hypothesis.

## Acceptance Checklist

- [ ] `tools/run_match.py --seed 42 --agents bots/starter/main.py bots/random_hold/main.py --replay-out runs/manual_viewer.json` writes a viewer artifact.
- [ ] `viewer/index.html` loads a replay from the file input.
- [ ] Canvas renders planets, fleets, comets, the sun, and ownership.
- [ ] Timeline scrubbing changes the rendered state.
- [ ] Play/pause advances frames.
- [ ] Metrics panel changes with the current frame.
- [ ] Issue list and jump controls show known issues when present.
- [ ] Notes can be added for the current step and exported as JSON.
- [ ] README documents the viewer workflow.
- [ ] Browser verification confirms the page is not blank and controls work.

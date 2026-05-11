# Orbit Wars Lab

Tournament, simulator, analytics, and visual review lab for the Kaggle Orbit Wars competition.

## Quick Start

```powershell
py -3.11 -m venv .venv-ow
.venv-ow\Scripts\python -m pip install --upgrade pip
.venv-ow\Scripts\python -m pip install -r requirements-ow-dev.txt
.venv-ow\Scripts\python -m pytest tests -q
```

## Run A Match

```powershell
.venv-ow\Scripts\python tools\run_match.py --seed 42 --agents bots/starter/main.py bots/random_hold/main.py
```

Export a replay for the visual viewer:

```powershell
.venv-ow\Scripts\python tools\run_match.py --seed 42 --agents bots/starter/main.py bots/random_hold/main.py --matchup starter_vs_hold --replay-out runs/manual_viewer.json
```

## Run A Tournament

```powershell
.venv-ow\Scripts\python tools\run_tournament.py --config config\tournament_default.json
```

Analyze a run directory:

```powershell
.venv-ow\Scripts\python tools\analyze_run.py runs\<run_id> --focus-agent bots/our_v1/main.py
```

## Visual Viewer

Start a local static server from the repo root:

```powershell
.venv-ow\Scripts\python -m http.server 8765 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:8765/viewer/index.html?replay=/runs/manual_viewer.json
```

The viewer renders the board, sun danger zone, planets, fleets, timeline, player telemetry, nearby issues, and review notes using a cherry red, light red, black, and white interface.

## Build Plan

The month-long simulator plan is in `docs/superpowers/plans/2026-05-11-orbit-wars-simulator-lab.md`.

The visual simulator layer plan is in `docs/superpowers/plans/2026-05-11-orbit-wars-visual-simulator-layer.md`.

# Visual Review Loop

Use the viewer after any candidate run that changes strategy. The goal is to turn watched mistakes into measurable bot work.

1. Export a replay:

```powershell
.venv-ow\Scripts\python tools\run_match.py --seed 42 --agents bots/our_v1/main.py bots/starter/main.py --replay-out runs/manual_viewer.json
```

2. Open the viewer and load `runs/manual_viewer.json`.

3. Review these checkpoints:

- Step 0-60: expansion speed, first launch angle, early neutral selection.
- Step 50, 150, 250, 350, 450: comet timing and comet overcommit.
- Any issue marker: watch at least 10 turns before the marker.
- Flaw Signals panel: inspect every `P1` and repeated `P2` before trusting a win.
- Bot Compare panel: check whether the winner is ahead on production, map control, or only temporary fleet pressure.
- Final 80 turns: scoring conversion, stranded fleets, over-defense.

4. Add notes with a specific category and turn.

5. Convert repeated notes into one of:

- A new detector in `src/orbitlab/detectors.py`.
- A replay detector in `src/orbitlab/replay_analysis.py`.
- A tactical hypothesis for the bot.
- A tournament config that isolates the weakness.

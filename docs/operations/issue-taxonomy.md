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

## Replay Flaw Detectors

| Detector | Severity | Meaning |
| --- | --- | --- |
| `bad_launch_sun_lane` | P1 | Launch ray crosses the sun danger radius before reaching the far side of the board. |
| `sun_death` | P1 | Fleet disappeared on a segment predicted to cross the sun danger radius. |
| `missed_comet_window` | P2 | Neutral comet was close to an owned planet with enough ships and no launch was made from that planet. |
| `slow_expansion` | P2 | Bot still owned one or fewer planets after the early expansion threshold. |
| `idle_overstock` | P2 | High-production planet hoarded a large garrison without launching for several frames. |
| `fleet_disappeared_without_capture` | P2 | Fleet disappeared without a predicted sun/out-of-bounds cause and without capturing a planet. |
| `late_trailing_no_pressure` | P2 | Bot was behind late but had little or no fleet pressure on the board. |
| `overdefended_low_production` | P3 | Low-production planet held a large garrison while the bot trailed in map control. |

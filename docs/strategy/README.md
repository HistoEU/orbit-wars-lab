# Orbit Wars Strategy Variant Plans

These are full Codex-ready implementation plans for the five biggest bot strategy variants worth building in the lab. They are written as standalone files so one can be handed to a fresh Codex session without needing the rest of this conversation.

Use them in this order:

1. `01-economy-expansion-snowball.md` - build the economy baseline that every other strategy has to beat.
2. `02-safe-geometry-pathfinder.md` - harden route planning so the bot stops wasting ships.
3. `03-comet-tempo-harvester.md` - add selective comet capture and denial.
4. `04-pressure-raider.md` - build tactical attacks that punish passive bots.
5. `05-adaptive-meta-controller.md` - combine the best modules into the main submission candidate.

Each file includes:

- exact bot file targets,
- the strategic identity,
- mechanics the planner must account for,
- build ideas,
- TDD task order,
- tournament commands,
- viewer analytics,
- flaw detection targets,
- concrete goals at the bottom.

The important rule: do not jump straight to the adaptive bot. Build the single-strategy variants first, measure them, then merge the parts that are actually strong.

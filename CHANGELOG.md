# Changelog

## 0.1.0 — 2026-09-27

- Define the three benchmark tasks: `keypress-ldr`, `piano-seq`, and `pick-place-ab`.
- Set protocol defaults to 20 trials for each keyboard task and 30 total trials for pick-and-place (10 per object).
- Report piano MIDI velocity, medium-force hit rate, within-trial spread, and per-finger across-trial statistics without using velocity to determine success.
- Add deterministic event-based scorers, per-trial MCAP output, and group JSON summaries.
- Add no-physics mock/scripted example, configurable OpenAI-compatible LLM policy, teleoperation adapter hook, and source-timed MCAP replay policy.
- Document task, data, clock-sync, session-metadata, and hardware reference contracts.

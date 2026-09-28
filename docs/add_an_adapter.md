# Add a hand, simulator, or rig

An adapter maps the DexBench action space to one configured embodiment, reads sensors, and emits timestamped `Event` records. Install DexBench in the adapter's environment, then pass its factory to the runner:

```bash
dexbench run \
  --task keypress-ldr \
  --policy llm \
  --adapter my_robot.dexbench_adapter:create_adapter \
  --trials 20 \
  --calib-id session-2026-09-27-a \
  --session-metadata session.json
```

The factory receives the parsed `session.json` mapping and returns an object with `name`, `reset`, `observe`, `execute`, and `close` methods as defined in [SPEC.md](../SPEC.md). `reset` returns the monotonic `t0` timestamp. `observe` returns `(now_ns, newly_available_events)`. `execute` returns the command and sensor events it produced. Use the same monotonic clock for all timestamps. Real-hardware sessions must set a nonempty calibration ID both in the JSON file and on the command line.

An adapter must convert or reject unsupported actions, clamp commands to a reviewed range, enforce its robot's e-stop and workspace limits, and raise on disconnects. It should not accept arbitrary joint vectors from an LLM. The included LLM policy only requests a single finger press; a rig adapter maps that request to its own fixed, configured motion primitive.

For an operator baseline, also implement `teleop_action(observation) -> Action | None`; returning `None` ends the trial. `reset_teleop()` is optional and may prepare the glove/leader input between trials. For replay, accept `Action(kind="replay_command", parameters={"topic": ..., "data": ...})` and dispatch only the configured `/hand/command` or `/arm/command` schemas.

For Wuji Hand 2, record `/hand/command` and `/hand/state` separately. Read USB keyboard input with evdev on a dedicated keyboard, not the host keyboard. For piano tasks, report MIDI note, velocity, note-off, and source timestamp. For pick-and-place, provide `/scorer/tray_state` from a calibrated depth-plus-color tray scorer and `/hand/state` release evidence. Preserve tactile data in `/hand/tactile`.

The initial repository does not include a vendor hardware driver. Keep those drivers in a separate rig package while using the shared scorer and MCAP contract here.

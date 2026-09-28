# Connect a hand, simulator, or rig

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

For real-hardware runs, fill in the hardware, calibration, clock method, channel offsets, and residuals in the [session template](../hardware/session.template.json). The runner checks these fields before loading the adapter.

An adapter must convert or reject unsupported actions, clamp commands to a reviewed range, enforce its robot's e-stop and workspace limits, and raise on disconnects. It should not accept arbitrary joint vectors from an LLM. The included LLM policy only requests a single finger press; a rig adapter maps that request to its own fixed, configured motion primitive.

For an operator baseline, also implement `teleop_action(observation) -> Action | None`; returning `None` ends the trial. `reset_teleop()` is optional and may prepare the leader input between trials. For replay, accept `Action(kind="replay_command", parameters={"topic": ..., "data": ...})` and dispatch only the configured `/hand/command` or `/arm/command` schemas.

For Wuji Hand 2, record `/hand/command` and `/hand/state` separately. Read the dedicated USB keyboard with evdev, not GUI key bindings on the host keyboard. Emit only evdev value `1` as `kind=key_down`, value `0` as `key_up`, and value `2` as `key_repeat`; never turn a held-key repeat into another down event. For piano tasks, report MIDI note, velocity, note-off, and source timestamp. Instruct the operator to play with even, medium force by feel; velocity is reported but does not affect task success. For pick-and-place, provide `/scorer/tray_state` from a calibrated D435 depth scorer (add color differencing if the marker is too hard to distinguish) and `/hand/state` release evidence. Preserve tactile data in `/hand/tactile`.

## Add a task policy

The built-in GPT-6 Astra and scripted policies support `keypress-ldr`. Supply a custom policy factory to run a policy for `piano-seq` or `pick-place-ab`, or to connect another learned policy:

```bash
dexbench run \
  --task piano-seq \
  --policy custom \
  --policy-factory my_project.policies:create_policy \
  --adapter my_robot.dexbench_adapter:create_adapter \
  --trials 20 \
  --calib-id session-2026-09-27-a \
  --session-metadata session.json
```

The policy factory receives the session metadata dictionary and returns an object with `name`, `reset(task, trial_id)`, and `act(observation)` methods. `act` returns an `Action` or `None`. The observation contains the task instruction, recent timestamped events, and run metadata; for `pick-place-ab`, `observation.metadata` includes the selected `object_id` and `grasp_type`. Robot-specific action kinds are handled by the adapter. Implement the policy and factory in an importable Python module in the environment running DexBench.

See [SPEC.md](../SPEC.md) for the shared task event fields and outcome rules.

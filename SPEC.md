# RC DexBench Interface and Scoring Specification

Version 0.1.0

This repository implements the benchmark workflow and reference scorers from the RC DexBench operating specification. Physical task definitions are fixed before a baseline run. Record actual dimensions, model numbers, settings, calibration, and photos in each hardware/session record. Do not tune the task after inspecting results.

## Core interfaces

An adapter connects DexBench to a robot or simulator. A policy reads an `Observation` and returns one bounded `Action` or `None` to stop. Adapter event timestamps and action timestamps use the same monotonic clock.

```python
class Adapter:
    name: str

    def reset(self, task: str, trial_id: str, metadata: dict) -> int: ...  # t0, monotonic ns
    def observe(self) -> tuple[int, list[Event]]: ...  # now_ns, newly available events
    def execute(self, action: Action) -> list[Event]: ...
    def close(self) -> None: ...


class Policy:
    name: str

    def reset(self, task: str, trial_id: str) -> None: ...
    def act(self, observation: Observation) -> Action | None: ...
```

The Python versions of these contracts live in `dexbench.models`. A hardware adapter factory is loaded with `--adapter package.module:factory` and is called with the session metadata dictionary. `execute` must enforce that policy actions remain within the rig's configured limits. Adapters may expose only the observations/actions supported by the hardware; they should not fabricate sensor events.

## Event format

Each MCAP message uses the `json` message encoding and a JSON object with:

```json
{
  "topic": "/keyboard/events",
  "timestamp_ns": 1234567890,
  "data": {"kind": "key_down", "key": "LEFT"}
}
```

The MCAP message's log and publish times equal `timestamp_ns`. Timestamps are nanoseconds on the session's shared monotonic clock. Preserve every channel's native sample rate and timestamp. Do not resample when recording. If channels have clock offsets, preserve each original timestamp and include channel-to-reference `index` and `time_diff_ms` alignment records in session metadata so alignment error can be measured instead of hidden.

Common topics:

| Topic | Example fields | Source |
| --- | --- | --- |
| `/hand/command` | `finger`, commanded position/effort, `pressed` | Hand command |
| `/hand/state` | joint positions, open pose, `open` boolean | Hand feedback |
| `/hand/tactile` | tactile array; optional `force_n` summary for MIDI correlation | Hand tactile sensor |
| `/keyboard/events` | `kind=key_down`, `key` | USB keyboard hardware |
| `/midi/events` | `kind=note_on`, `note`, `velocity` | MIDI keyboard hardware |
| `/arm/command`, `/arm/state` | command/state and units | Arm controller |
| `/glove/*` | glove skeleton, tactile, EMF, IMU | Operator glove |
| `/camera/*` | image data and camera timestamps | Camera adapter |
| `/scorer/tray_state` | `object_inside`, `stable_duration_s` | Depth + color scorer |
| `/dexbench/actions` | policy action and step | DexBench runner |
| `/dexbench/policy_trace` | model, request, response | Example LLM policy |

Scorers require these event fields: keyboard `key` values are uppercase `LEFT`, `DOWN`, or `RIGHT`; MIDI `note` and `velocity` are integers; `/hand/command` uses `finger` and `pressed`; `/hand/state` uses `open` as a boolean; `/scorer/tray_state` uses boolean `object_inside` and numeric `stable_duration_s`. Put fields inside the event's `data` object. Emit `/dexbench/invalid` with a `reason` string for hardware faults.

One `.mcap` contains one benchmark trial and all available channels. One `results.json` contains the policy/task group summary and references each trial file. Keep every success, failure, and invalid hardware trial; mark hardware faults invalid with a reason.

## Trial protocol

1. Before a session, calibrate clock offsets and record the method, residual, hardware, frame names, and `calib_id`.
2. Return the hand/arm to its defined start state. For pick-and-place, a person returns the object to its taped zone A marker.
3. Start MCAP recording with task, policy, trial ID, run type, and calibration ID.
4. Issue the start signal and set `t0` at that instant.
5. Let the selected policy control the robot; score the task from event channels.
6. Stop recording on success or timeout and write the outcome. A hardware fault is marked `invalid` with a reason and excluded from the success-rate denominator. Do not delete or rerun it.

For replay, select the successful teleop trial with median completion time from that round. Keep the same rig and calibration between teleop and replay. The JSON summary should report the source trial ID.

## Task definitions

### `keypress-ldr`

Use a dedicated USB keyboard read by evdev. Index presses LEFT, middle presses DOWN, and ring presses RIGHT. A trial succeeds if exactly three key-down events appear in that order within 10 seconds of `t0`. A wrong key, repeated/extra press, or timeout fails. Run 20 trials per policy without a scene reset. Report success rate, `t0`-to-third-key completion time, and per-finger `/hand/command` onset to keyboard-event latency.

This fixed sequence and hand pose can be memorized. It measures finger-level control precision and latency, not generalization.

### `piano-seq`

Use a velocity-sensitive MIDI keyboard with its model and velocity curve recorded and held fixed. Index, middle, and ring play C4, D4, E4 (MIDI 60, 62, 64), one note each and in order, within 10 seconds. No extra notes are allowed.

Set an even, medium force using touch; do not display MIDI velocity to the operator. Velocity is a measurement and does not change success. Run 20 trials per policy without a scene reset. Report success rate, completion time, per-finger latency, within-trial velocity standard deviation, mean and standard deviation of each assigned finger's velocity across trials, the fraction of notes with velocity 50–90, and tactile-to-velocity correlation when tactile samples are available.

### `pick-place-ab`

Use three objects: a standard tennis ball (about 6.7 cm, whole-hand grasp), a standard 3×3 Rubik's cube (about 5.7 cm and 100 g, whole-hand grasp), and a thick capped whiteboard marker (fingertip pinch). Record the brand and measured dimensions. Place the object at zone A in its fixed orientation. Start with the arm at home and hand open. Within 60 seconds, success requires the whole object inside the zone B tray, the hand returned to its open pose, and the tray region stable for one continuous second. Score the tray with D435 depth; add color differencing if the marker's depth signal is too weak, using a tray with strong color contrast. Calibrate the threshold with one empty-tray recording and one recording for each object; set the threshold to half the weakest signal. Run 10 trials per object (30 total), with a manual reset. Report success by object and grasp type and completion time.

## Results and baselines

Write one group JSON and one MCAP per trial. Teleoperation provides the human reference, replay measures system repeatability, and learned policies are evaluated against the same task metrics. The scripted policy and mock adapter provide deterministic examples of the recording and scoring workflow.

# RC DexBench Interface and Scoring Specification

Version 0.1.0 — initial public software contract

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
| `/hand/state` | joint positions, open pose, contact state | Hand feedback |
| `/hand/tactile` | tactile array or summarized force in N | Hand tactile sensor |
| `/keyboard/events` | `kind=key_down`, `key` | USB keyboard hardware |
| `/midi/events` | `kind=note_on`, `note`, `velocity` | MIDI keyboard hardware |
| `/arm/command`, `/arm/state` | command/state and units | Arm controller |
| `/glove/*` | glove skeleton, tactile, EMF, IMU | Operator glove |
| `/camera/*` | image data and camera timestamps | Camera adapter |
| `/scorer/tray_state` | `object_inside`, `stable_duration_s` | Depth + color scorer |
| `/dexbench/actions` | policy action and step | DexBench runner |
| `/dexbench/policy_trace` | model, request, response | Example LLM policy |

One `.mcap` contains one trial and all available channels. One `results.json` contains the policy/task group summary and references each trial file. Use `run_type=benchmark` and keep every success, failure, and invalid hardware trial. Dataset exports are separate: they contain successful episodes only and use `run_type=dataset`.

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

### `piano-seq-3`

Use a velocity-sensitive MIDI keyboard with its model and velocity curve recorded and held fixed. Index, middle, and ring play C4, D4, E4 (MIDI 60, 62, 64), one note each and in order, within 10 seconds. No extra notes are allowed. Run 20 trials per policy without a scene reset. Report success rate, completion time, per-finger latency, each note's velocity, and tactile-to-velocity correlation where tactile samples are available.

### `piano-seq-dyn`

Use the `piano-seq-3` setup and sequence. Success also requires each velocity inside the locked band. The initial band is 60–80. Before the official run, complete five practice trials; if none are inside the band, widen to 50–90 and lock that band before collecting benchmark results. Run 20 teleop trials. Replay is shared with `piano-seq-3`. Report velocity hit rate and velocity standard deviation.

### `pick-place-ab`

Start with the arm at home, the hand open, and the selected object in its fixed orientation at zone A. Within 60 seconds, success requires the whole object inside the zone B tray, the hand returned to its open pose, and the tray region stable for one continuous second. Use combined depth and color differencing; thin card/key objects are not reliably scored from depth alone. Calibrate the tray threshold from an empty tray and each of the six objects in the tray; set the threshold to half the weakest signal. Run 10 trials per object (60 total), with a manual reset. Report success by object/grasp type, completion time, failure type, and recovery after a failed grasp attempt.

## Results and baselines

Report one group JSON and every trial MCAP. Teleop is the human upper-bound reference. Replay is the system-repeatability/latency-floor reference. Learned-policy results remain open until measured. Mock and scripted outcomes are pipeline demonstrations and are not comparable benchmark scores.

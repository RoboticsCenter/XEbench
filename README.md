<p align="center">
  <img src="assets/robotics-center-logo.png" alt="Robotics Center" width="360">
</p>

# RC XEbench — Cross-Embodiment Benchmark

<p align="center">
  <a href="https://github.com/RoboticsCenter/XEbench/actions/workflows/lint.yml"><img src="https://github.com/RoboticsCenter/XEbench/actions/workflows/lint.yml/badge.svg?branch=main" alt="CI status"></a>
  <a href="https://github.com/RoboticsCenter/XEbench/actions/workflows/lint.yml"><img src="https://github.com/RoboticsCenter/XEbench/actions/workflows/lint.yml/badge.svg?branch=main&amp;job=docs" alt="Documentation check status"></a>
  <img src="https://img.shields.io/badge/status-alpha-orange" alt="Alpha status">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10 and newer">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-green.svg" alt="Apache 2.0 license"></a>
</p>

RC XEbench (Cross-Embodiment Benchmark) evaluates how one robotic manipulation policy performs across different robot bodies. Its headline cross-embodiment statistic is **σ: the spread in a policy's task success rate across eligible embodiments**, reported alongside **mean success and embodiment coverage**. Evaluate teleoperation, replay, and learned policies under the same protocol on different hands and arm-and-hand systems.

XEbench measures finger-level contact and force control, plus fixed-scene arm-and-hand pick-and-place. The benchmark records MIDI velocity, keyboard events, tactile measurements, command-to-contact latency, and clock alignment.

The Python package and command are `xebench`. Existing `dexbench` imports and commands, `DEXBENCH_*` environment variables, MCAP event topics, and submission schema identifiers remain supported for compatibility with recorded runs and existing integrations.

## Cross-embodiment score

**Same policy. Same task. Different bodies.** Measure task success on each embodiment, then report how much performance changes with the body. For pick and place, an embodiment is the complete arm + hand system; keyboard and piano tasks use the mounted hand and its fixture.

| Measure | What it tells you | Read it as |
| --- | --- | --- |
| **Cross-embodiment σ ↓** | Population standard deviation of per-body success rates | Lower σ means less variation between bodies; report in percentage points |
| **Mean success ↑** | Arithmetic mean of the same per-body success rates | Each eligible embodiment has equal weight |
| **Embodiment coverage** | Number and identity of eligible bodies | Compare policies on the same body set |

```text
SR_body (%) = 100 × successes / valid trials
mean_SR     = mean(SR_body)
σ_body      = √ mean((SR_body − mean_SR)²)
```

**Low σ alone does not establish a good policy:** consistent failure also produces low σ. Read consistency together with mean success, coverage, per-body uncertainty, and recordings. Human-relative throughput is reported separately against human teleoperation on each identical embodiment.

Use a controlled cohort: hold the task, protocol, scene distribution, scoring rules, and checkpoint fixed; disclose every embodiment adapter. For the RC cross-embodiment summary, the proposed publication floor is at least **three eligible embodiments** and **40 valid trials per body × policy × task cell**. Compare policy columns over their common eligible body set. Different checkpoints or fine-tuning per body must be labeled as an adapted-policy comparison, rather than zero-shot transfer.

The CLI records and scores individual runs; it does not compute a fleet-level σ from a single run. See the [cross-embodiment evaluation page](https://dexterity.roboticscenter.ai/benchmark) for the matrix, cohort rules, human baseline, and inspectable results. Its preview and XE-Table demonstration values are illustrative, not measured benchmark results. The detailed aggregation contract is in [SPEC.md](SPEC.md#cross-embodiment-evaluation).

## Tasks

| Task | Goal | Trials per policy | Setup | Automatic outcome |
| --- | --- | ---: | --- | --- |
| `keypress-ldr` | Index, middle, ring press LEFT → DOWN → RIGHT | 20 | [Rig setup](hardware/keypress-ldr.md) | Dedicated USB keyboard events |
| `piano-seq` | Play MIDI notes 60 → 62 → 64 with even, medium force | 20 | [Rig setup](hardware/piano-seq.md) | MIDI note, timestamp, and velocity events |
| `pick-place-ab` | Move a tennis ball, 3×3 cube, or capped whiteboard marker from zone A into a tray | 10 per object (30 total) | [Rig setup](hardware/pick-place-ab.md) | Tray region, hand release, and stability signals |

Task protocols and measurable outcomes are in [SPEC.md](SPEC.md). See [recordings and scoring](docs/recordings-and-scoring.md) for benchmark result files and clock alignment.

## Task clips and rig photo

Each square GIF shows its matching task. The photo shows the robot hand and arm rig.

### `keypress-ldr`

![Dexterous hand above the arrow-key keyboard for keypress-ldr](assets/keypress-ldr.gif)

### `piano-seq`

![Dexterous hand above the MIDI keyboard for piano-seq](assets/piano-seq.gif)

### `pick-place-ab`

![Wuji dexterous hand mounted on a robot arm, the pick-place-ab rig reference](assets/pick-place-ab-rig.jpg)

## Quick start

Install from a fresh checkout with Python 3.10 or later:

```bash
git clone https://github.com/RoboticsCenter/XEbench.git xebench
cd xebench
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
xebench tasks
```

Run the bundled pipeline example and inspect its per-trial MCAP and JSON summary:

```bash
xebench run --task keypress-ldr --policy scripted --adapter mock --trials 2
xebench score --task keypress-ldr --mcap runs/<run-id>/trial-001.mcap
```

The scripted policy and mock adapter generate synthetic events to demonstrate the recording and scoring workflow.

Real-robot runs use an adapter for the hand, sensors, and arm in the configured rig. See [Connect a hand or rig](docs/add_an_adapter.md) for the adapter interface.

## LLM example policy

The built-in GPT-6 Astra policy is an example for `keypress-ldr`. It uses the OpenAI Chat Completions API and returns one bounded `press` action at a time for `index`, `middle`, or `ring`; the adapter maps that action to the robot's configured finger motion. Use a [custom policy factory](docs/add_an_adapter.md#add-a-task-policy) for `piano-seq`, `pick-place-ab`, or another policy. See the [GPT-6 Astra API documentation](https://developers.openai.com/api/docs/models/gpt-6-astra).

```bash
export XEBENCH_LLM_BASE_URL="https://api.openai.com/v1"
export OPENAI_API_KEY="<your-api-key>"
export XEBENCH_LLM_MODEL="gpt-6-astra"
export XEBENCH_LLM_REASONING_EFFORT="low"
xebench run --task keypress-ldr --policy llm --adapter mock --trials 1
```

The request and response are recorded on `/dexbench/policy_trace`; credentials are omitted. The policy accepts only the listed finger actions or `stop`. Replace `mock` with your robot adapter to connect the policy to a hand. See [the adapter guide](docs/add_an_adapter.md).

## Teleop and replay baselines

A robot adapter can expose `teleop_action(observation)` to collect an operator baseline. The replay policy reads the command stream from one successful teleop trial and preserves its original relative timing. To select the successful teleop trial closest to the median completion time and replay it on the same rig:

```bash
xebench run --task keypress-ldr --policy teleop \
  --adapter my_robot.xebench_adapter:create_adapter --trials 20 \
  --calib-id session-2026-09-27-a --session-metadata session.json

xebench run --task keypress-ldr --policy replay \
  --adapter my_robot.xebench_adapter:create_adapter --trials 20 \
  --calib-id session-2026-09-27-a --session-metadata session.json \
  --replay-results runs/<teleop-run-id>/results.json
```

The replay command checks the task, calibration ID, and hardware metadata against the teleop run. For piano-seq, it selects a successful teleop episode with median completion time, just as it does for the other tasks.

## Results

Keep every trial in the run's `results.json`, including failures and hardware-invalid trials. Upload MCAPs to [DexData](https://dexdata.roboticscenter.ai), then submit a complete real-robot run to the [Dexterity benchmark leaderboard](https://dexterity.roboticscenter.ai/benchmark). The page accepts standard tasks and custom protocols that follow the submission format, validates the per-trial outcomes, and recalculates the public score. See the [submission instructions](results/README.md) and the [submission JSON Schema](results/submission.schema.json) for the exact required fields and format.

| Recorded example | Label in source run | MCAP |
| --- | --- | --- |
| Episode 4 | Success | [View recording](examples/keypress-ldr/episode_4_success.mcap) |
| Episode 5 | Failure | [View recording](examples/keypress-ldr/episode_5_failure.mcap) |

These recordings are examples, not XEbench-scored results or a complete benchmark round. The source GUI logger may report repeated key events while a key is held; see the [example notes](examples/keypress-ldr/) and the key-repeat event contract in [SPEC.md](SPEC.md#event-format).

## Baselines and protocol

Each policy run writes one JSON summary and one MCAP per trial. Benchmark runs keep failures. The reference baselines are:

- **Teleop:** a human operator using the same robot and task setup. Its run can be generated by a hardware adapter that maps the operator's controls into XEbench actions.
- **Replay:** open-loop playback of the `/hand/command` stream, plus `/arm/command` for pick-and-place, from the successful teleop episode with the median completion time. Keep hardware and calibration fixed between source and replay runs.
- **Learned policy:** report the model, weights, endpoint/provider, prompt or policy version, action limits, and all run settings.

Replay and operator control are adapter-level capabilities because command units depend on the robot. The result format and scoring are shared. See the [interface specification](SPEC.md).

For piano-seq, report each note's MIDI velocity, within-trial velocity standard deviation, the mean and standard deviation across trials for each assigned finger, the fraction of notes with velocity 50–90, and tactile-to-velocity correlation when tactile data is available. Velocity is a reported measure and does not affect task success.

## Add a hand or task

- [Connect a hand or rig](docs/add_an_adapter.md)
- [Add a task](docs/write_a_task.md)
- [Recordings and scoring](docs/recordings-and-scoring.md)
- [Hardware reference sheets](hardware/)

The command-line workflow is native to XEbench. Its packaging and benchmark workflow take inspiration from [Inspect Robots](https://github.com/robocurve/inspect-robots), [WorldEvals](https://github.com/robocurve/worldevals), and [StationeryBench](https://github.com/robocurve/stationerybench), while remaining independent so tactile and contact-event channels are part of its own event and scoring contract.

## License and citation

Released under the Apache License 2.0. See [LICENSE](LICENSE).

```bibtex
@software{rc_xebench,
  author = {{Robotics Center}},
  title = {RC XEbench: An Open Cross-Embodiment Benchmark for Robotic Manipulation},
  year = {2026},
  url = {https://github.com/RoboticsCenter/XEbench},
  version = {0.1.0},
  license = {Apache-2.0}
}
```

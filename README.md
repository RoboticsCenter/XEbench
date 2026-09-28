# RC DexBench

RC DexBench is an open benchmark and evaluation toolkit for dexterous robotic hands. It defines tasks, hardware and session metadata, event-based scoring, and a common adapter interface so teams can compare teleoperation, replay, and learned policies with the same protocol.

The initial task suite focuses on finger-level contact and force control, then extends to fixed-scene arm-and-hand pick-and-place. MIDI velocity, keyboard events, tactile measurements, command-to-contact latency, and clock alignment are part of the benchmark record.

> **Status:** early research release. The task definitions and scorers are available now. The included mock is for trying the software path and is not a physical result. Wuji Hand 2, keyboard, MIDI, and YAM drivers are supplied as external adapter examples, not claimed as included production drivers. No DexBench Teleop, Replay, or learned-policy result has been run or published in this repository yet.

## Tasks

| Task | Goal | Trials per policy | Automatic outcome |
| --- | --- | ---: | --- |
| `keypress-ldr` | Index, middle, ring press LEFT → DOWN → RIGHT | 20 | Dedicated USB keyboard events |
| `piano-seq-3` | Play MIDI notes 60 → 62 → 64 | 20 | MIDI note and timestamp events |
| `piano-seq-dyn` | Same sequence, each velocity in the locked band | 20 | MIDI notes and velocity |
| `pick-place-ab` | Move one of six objects from zone A into a tray | 10 per object | Tray region, hand release, and stability signals |

Task protocols and measurable outcomes are in [SPEC.md](SPEC.md). Physical setup and per-session recording fields are in [hardware/](hardware/) and [docs/data_and_scoring.md](docs/data_and_scoring.md).

## Quick start

Install from a fresh checkout with Python 3.10 or later:

```bash
git clone https://github.com/RoboticsCenter/dexbench.git
cd dexbench
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
dexbench tasks
```

Run the bundled pipeline example and inspect its per-trial MCAP and JSON summary:

```bash
dexbench run --task keypress-ldr --policy scripted --adapter mock --trials 2
dexbench score --task keypress-ldr --mcap runs/<run-id>/trial-001.mcap
```

The scripted policy and mock adapter have no physics and read no camera image. Their score only confirms that event recording and scoring work; it must not be reported as a DexBench robot result.

## LLM example policy

The example LLM policy uses an OpenAI Chat Completions-compatible endpoint and only returns one bounded action at a time (`press` with `index`, `middle`, or `ring`). It cannot return joint targets. Configure an endpoint, API key, and model in the environment; the same interface can use an Astra deployment when its endpoint supports the OpenAI-compatible Chat Completions request format.

```bash
export DEXBENCH_LLM_BASE_URL="https://api.openai.com/v1"
export DEXBENCH_LLM_API_KEY="<your-key>"
export DEXBENCH_LLM_MODEL="gpt-4.1-mini"
dexbench run --task keypress-ldr --policy llm --adapter mock --trials 1
```

The request and model response are recorded on `/dexbench/policy_trace`; credentials are never written into the trace. The model is an example policy, not a baseline result. Change `--adapter mock` to your adapter only after reviewing its action limits, workspace bounds, and stop behavior. See [the adapter guide](docs/add_an_adapter.md). The example uses the OpenAI-compatible Chat Completions endpoint and validates the returned JSON against the three allowed fingers; consult the provider's current API documentation when configuring an endpoint.

## Teleop and replay baselines

A robot adapter can expose `teleop_action(observation)` to collect an operator baseline. The replay policy reads the command stream from one successful teleop trial and preserves its original relative timing. To select the successful teleop trial closest to the median completion time and replay it on the same rig:

```bash
dexbench run --task keypress-ldr --policy teleop \
  --adapter my_robot.dexbench_adapter:create_adapter --trials 20 \
  --calib-id session-2026-09-27-a --session-metadata session.json

dexbench run --task keypress-ldr --policy replay \
  --adapter my_robot.dexbench_adapter:create_adapter --trials 20 \
  --calib-id session-2026-09-27-a --session-metadata session.json \
  --replay-results runs/<teleop-run-id>/results.json
```

The replay command checks the task, calibration ID, and hardware metadata against the teleop run. For `piano-seq-dyn`, a successful `piano-seq-3` teleop run may seed the shared replay baseline. Use `--velocity-band 50 90` only when the five-trial practice procedure requires it, and lock the selected band before official trials.

## Results

No physical results are included yet. Do not fill the table with mock outcomes. For each official task run, publish the run summary, all trial MCAPs including failures, the session calibration identifier, and rig photos/configuration. Mark hardware faults invalid with a written reason; do not delete or rerun failed trials.

| Task | Teleop | Replay | Learned policy |
| --- | --- | --- | --- |
| `keypress-ldr` | Pending | Pending | Open |
| `piano-seq-3` | Pending | Pending | Open |
| `piano-seq-dyn` | Pending | Pending | Open |
| `pick-place-ab` | Pending | Pending | Open |

## Baselines and protocol

Each policy run writes one JSON summary and one MCAP per trial. Benchmark runs keep failures. The reference baselines are:

- **Teleop:** a human operator using the same robot and task setup. Its run can be generated by a hardware adapter that maps the operator's controls into DexBench actions.
- **Replay:** open-loop playback of the `/hand/command` stream, plus `/arm/command` for pick-and-place, from the successful teleop episode with the median completion time. Keep hardware and calibration fixed between source and replay runs.
- **Learned policy:** report the model, weights, endpoint/provider, prompt or policy version, action limits, and all run settings.

Replay and operator control are intentionally adapter-level capabilities because the correct safety controls and command units depend on a robot. The result format and scoring are shared. See the [interface specification](SPEC.md).

## Add a hand or task

- [Connect a hand or rig](docs/add_an_adapter.md)
- [Add a task](docs/write_a_task.md)
- [Data channels, clocks, and scoring](docs/data_and_scoring.md)
- [Hardware reference sheets](hardware/)
- [Glove demonstration data setup](hardware/todo1.md)

The command-line workflow is native to DexBench. Its packaging and benchmark workflow take inspiration from [Inspect Robots](https://github.com/robocurve/inspect-robots), [WorldEvals](https://github.com/robocurve/worldevals), and [StationeryBench](https://github.com/robocurve/stationerybench), while remaining independent so tactile and contact-event channels are part of its own event and scoring contract.

## License and citation

Released under the Apache License 2.0. See [LICENSE](LICENSE).

```bibtex
@software{rc_dexbench,
  author = {{Robotics Center}},
  title = {RC DexBench: An Open Benchmark for Dexterous Robot Evaluation},
  year = {2026},
  url = {https://github.com/RoboticsCenter/dexbench},
  version = {0.1.0},
  license = {Apache-2.0}
}
```

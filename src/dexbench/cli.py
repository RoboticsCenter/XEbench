"""Command-line interface for running and scoring DexBench trials."""

from __future__ import annotations

import argparse
import importlib
import json
import statistics
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from dexbench.adapters import MockKeyboardAdapter, create_observation, load_adapter
from dexbench.models import Event, Policy
from dexbench.policies import (
    OpenAICompatiblePolicy,
    ReplayPolicy,
    ScriptedKeyboardPolicy,
    TeleopPolicy,
)
from dexbench.recording import read_mcap_events, write_json, write_mcap
from dexbench.tasks import OBJECT_GRASP_TYPE, TASKS, score_trial


def _policy(name: str, args: argparse.Namespace, session_metadata: dict[str, Any]) -> Policy:
    """Construct one of the included policies."""
    if name == "custom":
        if not args.policy_factory:
            raise ValueError("Custom policies require --policy-factory package.module:factory")
        module_name, separator, attribute_name = args.policy_factory.partition(":")
        if not separator:
            raise ValueError("Policy factory must be package.module:factory")
        factory = getattr(importlib.import_module(module_name), attribute_name)
        return factory(session_metadata)
    if args.policy_factory:
        raise ValueError("--policy-factory applies only with --policy custom")
    if name == "scripted":
        return ScriptedKeyboardPolicy()
    if name == "llm":
        return OpenAICompatiblePolicy()
    if name == "replay":
        if not args.replay_from:
            raise ValueError(
                "Replay policy requires --replay-from pointing to a successful source MCAP"
            )
        return ReplayPolicy(args.replay_from, args.replay_topics)
    if name == "teleop":
        return TeleopPolicy()
    raise ValueError(f"Unknown included policy: {name}")


def _event(topic: str, timestamp_ns: int, data: dict[str, Any]) -> Event:
    """Create a standard event record."""
    return Event(topic, timestamp_ns, data)


def _trial(
    task: str,
    trial_id: str,
    policy: Policy,
    adapter: Any,
    metadata: dict[str, Any],
    max_actions: int,
) -> tuple[list[Event], int, dict[str, Any]]:
    """Run one bounded trial and return its recorded events, t0, and score."""
    policy.reset(task, trial_id)
    t0_ns = adapter.reset(task, trial_id, metadata)
    start_data = {"task": task, "trial_id": trial_id, "t0": True}
    events = [_event("/dexbench/trial", t0_ns, start_data)]
    for step in range(max_actions):
        try:
            now_ns, fresh_events = adapter.observe()
        except Exception as error:
            events.append(
                _event(
                    "/dexbench/invalid",
                    time.monotonic_ns(),
                    {"reason": "adapter_observation_error", "error": str(error)},
                )
            )
            break
        events.extend(fresh_events)
        if now_ns - t0_ns >= int(TASKS[task]["limit_s"] * 1_000_000_000):
            events.append(_event("/dexbench/timeout", now_ns, {"limit_s": TASKS[task]["limit_s"]}))
            break
        if any(event.topic == "/dexbench/invalid" for event in fresh_events):
            break
        observation_events = sorted(events, key=lambda event: event.timestamp_ns)
        observation = create_observation(task, t0_ns, now_ns, observation_events, metadata)
        try:
            action = policy.act(observation)
        except Exception as error:
            events.append(
                _event(
                    "/dexbench/failure",
                    time.monotonic_ns(),
                    {"type": "policy_error", "error": str(error)},
                )
            )
            break
        trace = getattr(policy, "last_trace", None)
        action_ns = time.monotonic_ns()
        if trace:
            events.append(_event("/dexbench/policy_trace", action_ns, trace))
        if action is None:
            break
        events.append(
            _event(
                "/dexbench/actions",
                action_ns + (1 if trace else 0),
                {"step": step, "policy": policy.name, "action": action.to_dict()},
            )
        )
        try:
            events.extend(adapter.execute(action))
        except Exception as error:
            events.append(
                _event(
                    "/dexbench/invalid",
                    time.monotonic_ns(),
                    {"reason": "adapter_execution_error", "error": str(error)},
                )
            )
            break
        trial_score = score_trial(task, events, t0_ns)
        if trial_score.success or trial_score.invalid:
            break
    try:
        now_ns, fresh_events = adapter.observe()
        events.extend(fresh_events)
        if now_ns - t0_ns >= int(TASKS[task]["limit_s"] * 1_000_000_000) and not any(
            event.topic == "/dexbench/timeout" for event in events
        ):
            events.append(_event("/dexbench/timeout", now_ns, {"limit_s": TASKS[task]["limit_s"]}))
    except Exception as error:
        events.append(
            _event(
                "/dexbench/invalid",
                time.monotonic_ns(),
                {"reason": "adapter_observation_error", "error": str(error)},
            )
        )
    result = score_trial(task, events, t0_ns)
    if result.reason == "incomplete_sequence" and max_actions > 0:
        result = type(result)(False, "action_limit", result.metrics, result.invalid)
    return (
        sorted(events, key=lambda event: event.timestamp_ns),
        t0_ns,
        {
            "success": result.success,
            "reason": result.reason,
            "metrics": result.metrics,
            "invalid": result.invalid,
        },
    )


def _run(args: argparse.Namespace) -> int:
    """Run benchmark trials and save per-trial MCAP plus a run summary."""
    if args.task not in TASKS:
        raise ValueError(f"Unknown task {args.task!r}; use 'dexbench tasks' to see available tasks")
    trial_count = args.trials if args.trials is not None else _protocol_trials(args.task)
    if trial_count < 1 or args.max_actions < 1:
        raise ValueError("--trials and --max-actions must be positive")
    replay_results = None
    if args.policy == "replay" and args.replay_results:
        results_path = Path(args.replay_results)
        replay_results = json.loads(results_path.read_text(encoding="utf-8"))
        if replay_results.get("policy") != "teleop":
            raise ValueError("--replay-results must point to a teleop policy run")
        if replay_results.get("task") != args.task:
            raise ValueError(
                f"Replay source task {replay_results.get('task')!r} cannot seed {args.task!r}"
            )
        successes = [
            trial
            for trial in replay_results.get("trials", [])
            if trial.get("success")
            and not trial.get("invalid")
            and trial.get("metrics", {}).get("completion_time_s") is not None
        ]
        if not successes:
            raise ValueError("Teleop run has no successful trials with completion times to replay")
        median_time = statistics.median(
            trial["metrics"]["completion_time_s"] for trial in successes
        )
        source = min(
            successes,
            key=lambda trial: abs(trial["metrics"]["completion_time_s"] - median_time),
        )
        args.replay_from = str((results_path.parent / source["mcap"]).resolve())
        args.replay_source_trial_id = source["trial_id"]
    session_metadata = {}
    if args.session_metadata:
        session_metadata = json.loads(Path(args.session_metadata).read_text(encoding="utf-8"))
    if args.adapter != "mock" and (not args.calib_id or not args.session_metadata):
        raise ValueError("Real-hardware runs require --calib-id and --session-metadata")
    if args.adapter != "mock" and session_metadata.get("calib_id") != args.calib_id:
        raise ValueError("--calib-id must match the calib_id recorded in --session-metadata")
    if args.adapter != "mock":
        sync = session_metadata.get("sync", {})
        if not session_metadata.get("hardware") or not sync.get("method"):
            raise ValueError("Session metadata must include measured hardware and a sync method")
        if not sync.get("offset_ms_by_channel") or not sync.get("residual_ms_by_channel"):
            raise ValueError("Session metadata must include measured clock offsets and residuals")
    if replay_results is not None:
        source_calib = replay_results.get("calib_id")
        if source_calib != args.calib_id:
            raise ValueError(
                f"Replay and teleop must use the same calibration ID; source has {source_calib!r}"
            )
        source_hardware = replay_results.get("session_metadata", {}).get("hardware")
        current_hardware = session_metadata.get("hardware")
        if source_hardware != current_hardware:
            raise ValueError("Replay and teleop session hardware metadata must match")
    policy = _policy(args.policy, args, session_metadata)
    adapter = (
        MockKeyboardAdapter()
        if args.adapter == "mock"
        else load_adapter(args.adapter, session_metadata)
    )
    bind_adapter = getattr(policy, "bind_adapter", None)
    if callable(bind_adapter):
        bind_adapter(adapter)
    run_id = args.run_id or (
        f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:8]}"
    )
    output = Path(args.output) / run_id
    run_metadata = {
        "run_id": run_id,
        "task": args.task,
        "policy": policy.name,
        "adapter": adapter.name,
        "run_type": "benchmark",
        "calib_id": args.calib_id or "not-provided",
        "session_metadata": session_metadata,
        "mock": args.adapter == "mock",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "max_actions": args.max_actions,
        "policy_config": {
            "model": getattr(policy, "model", None),
            "endpoint": getattr(policy, "base_url", None),
            "reasoning_effort": getattr(policy, "reasoning_effort", None),
        },
    }
    if isinstance(policy, ReplayPolicy):
        run_metadata["replay_source_trial_id"] = getattr(
            args, "replay_source_trial_id", policy.source_trial_id
        )
        run_metadata["replay_source_mcap"] = str(Path(args.replay_from).resolve())
    trials = []
    try:
        for trial_number in range(1, trial_count + 1):
            trial_id = f"{run_id}-{trial_number:03d}"
            trial_metadata = dict(run_metadata)
            if args.task == "pick-place-ab":
                objects = TASKS[args.task]["objects"]
                trial_metadata["object_id"] = objects[(trial_number - 1) % len(objects)]
                trial_metadata["grasp_type"] = OBJECT_GRASP_TYPE[trial_metadata["object_id"]]
            events, t0_ns, outcome = _trial(
                args.task, trial_id, policy, adapter, trial_metadata, args.max_actions
            )
            mcap_path = output / f"trial-{trial_number:03d}.mcap"
            write_mcap(
                mcap_path,
                events,
                {**trial_metadata, "trial_id": trial_id, "t0_ns": t0_ns},
            )
            trials.append(
                {
                    "trial_id": trial_id,
                    "mcap": mcap_path.name,
                    "object_id": trial_metadata.get("object_id"),
                    "grasp_type": trial_metadata.get("grasp_type"),
                    **outcome,
                }
            )
    finally:
        adapter.close()
    valid = [trial for trial in trials if not trial["invalid"]]
    success_rate = sum(trial["success"] for trial in valid) / len(valid) if valid else None
    durations = [
        trial["metrics"]["completion_time_s"]
        for trial in valid
        if trial["metrics"].get("completion_time_s") is not None
    ]
    summary = {
        **run_metadata,
        "task_description": TASKS[args.task]["description"],
        "protocol_trials": _protocol_trials(args.task),
        "trials_per_object": TASKS[args.task].get("trials_per_object"),
        "trial_count": len(trials),
        "protocol_complete": len(trials) >= _protocol_trials(args.task),
        "invalid_count": len(trials) - len(valid),
        "success_rate": success_rate,
        "mean_completion_time_s": statistics.mean(durations) if durations else None,
        "sync_metrics": _sync_metrics(session_metadata),
        "success_rate_by_object": {
            object_id: _success_rate(
                [trial for trial in valid if trial.get("object_id") == object_id]
            )
            for object_id in TASKS[args.task].get("objects", [])
        },
        "success_rate_by_grasp_type": {
            grasp_type: _success_rate(
                [trial for trial in valid if trial.get("grasp_type") == grasp_type]
            )
            for grasp_type in sorted(set(OBJECT_GRASP_TYPE.values()))
            if args.task == "pick-place-ab"
        },
        "piano_velocity_by_finger": (
            _piano_velocity_summary(valid) if args.task == "piano-seq" else None
        ),
        "trials": trials,
    }
    write_json(output / "results.json", summary)
    print(json.dumps({"output": str(output), "summary": summary}, indent=2))
    return 0


def _success_rate(trials: list[dict[str, Any]]) -> float | None:
    """Calculate an invalid-excluding success rate for a trial subset."""
    return sum(trial["success"] for trial in trials) / len(trials) if trials else None


def _protocol_trials(task: str) -> int:
    """Return the fixed full-round trial count for a task."""
    if task == "pick-place-ab":
        return len(TASKS[task]["objects"]) * TASKS[task]["trials_per_object"]
    return TASKS[task]["trials"]


def _piano_velocity_summary(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize MIDI velocity by assigned finger over valid trials."""
    note_for_finger = {"index_C4": 60, "middle_D4": 62, "ring_E4": 64}
    values = {finger: [] for finger in note_for_finger}
    all_velocities = []
    for trial in trials:
        metrics = trial.get("metrics", {})
        all_velocities.extend(metrics.get("velocities", []))
        note_velocities = zip(metrics.get("notes", []), metrics.get("velocities", []), strict=False)
        for note, velocity in note_velocities:
            for finger, target_note in note_for_finger.items():
                if note == target_note:
                    values[finger].append(float(velocity))
    return {
        "note_count": len(all_velocities),
        "velocity_50_90_hit_rate": (
            sum(50 <= velocity <= 90 for velocity in all_velocities) / len(all_velocities)
            if all_velocities
            else None
        ),
        "by_finger": {
            finger: {
                "count": len(velocities),
                "mean": statistics.mean(velocities) if velocities else None,
                "stddev": statistics.pstdev(velocities) if velocities else None,
            }
            for finger, velocities in values.items()
        },
    }


def _sync_metrics(session_metadata: dict[str, Any]) -> dict[str, Any]:
    """Summarize the recorded absolute sample alignment offsets by channel."""
    alignment = session_metadata.get("sync", {}).get("alignment", {})
    metrics = {}
    for channel, values in alignment.items():
        if not isinstance(values, dict):
            continue
        offsets = [
            abs(float(value))
            for value in values.get("time_diff_ms", [])
            if isinstance(value, (int, float))
        ]
        if offsets:
            metrics[channel] = {
                "sample_count": len(offsets),
                "median_abs_error_ms": statistics.median(offsets),
                "max_abs_error_ms": max(offsets),
            }
    return metrics


def _score(args: argparse.Namespace) -> int:
    """Rescore one trial MCAP using its stored t0 timestamp."""
    path = Path(args.mcap)
    events = read_mcap_events(path)
    t0_event = next(
        (event for event in events if event.topic == "/dexbench/trial" and event.data.get("t0")),
        None,
    )
    if t0_event is None:
        raise ValueError(f"{path} does not contain a DexBench trial start record")
    score = score_trial(args.task, events, t0_event.timestamp_ns)
    print(
        json.dumps(
            {
                "task": args.task,
                "success": score.success,
                "reason": score.reason,
                "metrics": score.metrics,
            },
            indent=2,
        )
    )
    return 0


def _tasks(_args: argparse.Namespace) -> int:
    """List the reference tasks and their purposes."""
    for name, definition in TASKS.items():
        print(f"{name:16} {definition['description']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the DexBench argument parser."""
    parser = argparse.ArgumentParser(
        prog="dexbench", description="Run and score dexterous hand tasks"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    tasks_parser = commands.add_parser("tasks", help="list included benchmark tasks")
    tasks_parser.set_defaults(func=_tasks)
    run_parser = commands.add_parser("run", help="run a benchmark policy on an adapter")
    run_parser.add_argument("--task", required=True, choices=TASKS)
    run_parser.add_argument(
        "--policy", required=True, choices=("scripted", "llm", "teleop", "replay", "custom")
    )
    run_parser.add_argument(
        "--policy-factory", help="custom policy factory as package.module:factory"
    )
    run_parser.add_argument(
        "--adapter", default="mock", help="mock or Python module:factory adapter"
    )
    run_parser.add_argument(
        "--trials", type=int, help="trial count (defaults to the task's full protocol)"
    )
    run_parser.add_argument("--max-actions", type=int, default=12)
    run_parser.add_argument("--output", default="runs")
    run_parser.add_argument("--run-id")
    run_parser.add_argument("--calib-id")
    run_parser.add_argument(
        "--session-metadata", help="JSON with session hardware and sync metadata"
    )
    run_parser.add_argument("--replay-from", help="successful source-trial MCAP for replay policy")
    run_parser.add_argument(
        "--replay-results", help="teleop results.json; select the successful median-time trial"
    )
    run_parser.add_argument("--replay-topics", nargs="+", default=["/hand/command", "/arm/command"])
    run_parser.set_defaults(func=_run)
    score_parser = commands.add_parser("score", help="rescore one trial MCAP")
    score_parser.add_argument("--task", required=True, choices=TASKS)
    score_parser.add_argument("--mcap", required=True)
    score_parser.set_defaults(func=_score)
    return parser


def main() -> None:
    """Run the command-line application."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        status = args.func(args)
    except (ValueError, OSError, httpx.HTTPError, KeyError, ImportError) as error:
        print(f"dexbench: error: {error}", file=sys.stderr)
        status = 2
    raise SystemExit(status)

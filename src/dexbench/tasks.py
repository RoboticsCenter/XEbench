"""Reference task definitions and deterministic scorers."""

from __future__ import annotations

import math
from typing import Any

from dexbench.models import Event, Score

TASKS: dict[str, dict[str, Any]] = {
    "keypress-ldr": {
        "description": "Press LEFT, DOWN, RIGHT with index, middle, ring fingers in order.",
        "limit_s": 10.0,
        "trials": 20,
        "event_topic": "/keyboard/events",
        "sequence": ["LEFT", "DOWN", "RIGHT"],
    },
    "piano-seq": {
        "description": "Play MIDI notes C4, D4, E4 (60, 62, 64) in order with even, medium force.",
        "limit_s": 10.0,
        "trials": 20,
        "event_topic": "/midi/events",
        "sequence": [60, 62, 64],
    },
    "pick-place-ab": {
        "description": "Pick the object at zone A and place it fully inside the zone B tray.",
        "limit_s": 60.0,
        "trials_per_object": 10,
        "objects": [
            "tennis_ball",
            "rubiks_cube_3x3",
            "whiteboard_marker",
        ],
        "event_topic": "/scorer/tray_state",
    },
}

INSTRUCTIONS = {
    "keypress-ldr": (
        "Use index for LEFT, middle for DOWN, and ring for RIGHT. Press each once in order. "
        "Finish within 10 seconds. You may only request a press action for one of those fingers."
    ),
    "piano-seq": (
        "Play C4 (60), D4 (62), E4 (64), once each and in order, within 10 seconds. "
        "Use an even, medium force for each key, guided by feel rather than a numeric display."
    ),
    "pick-place-ab": (
        "Pick up the designated object at zone A, move it to the zone B tray, release it, "
        "and leave it stable for one continuous second. Finish within 60 seconds."
    ),
}

FINGER_FOR_KEY = {"LEFT": "index", "DOWN": "middle", "RIGHT": "ring"}
OBJECT_GRASP_TYPE = {
    "tennis_ball": "power_grasp",
    "rubiks_cube_3x3": "power_grasp",
    "whiteboard_marker": "precision_pinch",
}


def _select(events: list[Event], topic: str) -> list[Event]:
    """Select events on one channel and sort them by source timestamp."""
    return sorted((event for event in events if event.topic == topic), key=lambda e: e.timestamp_ns)


def _completion(events: list[Event], t0_ns: int, final_ns: int | None) -> float | None:
    """Return elapsed completion time from t0, if the task has a completion event."""
    if final_ns is None:
        return None
    return max(0.0, (final_ns - t0_ns) / 1_000_000_000)


def _latencies(events: list[Event], t0_ns: int, key_events: list[Event]) -> dict[str, float | None]:
    """Measure command-to-contact delay for the three designated fingers."""
    commands = _select(events, "/hand/command")
    latency: dict[str, float | None] = {finger: None for finger in FINGER_FOR_KEY.values()}
    for event, key in zip(key_events, ("LEFT", "DOWN", "RIGHT"), strict=False):
        finger = FINGER_FOR_KEY[key]
        candidates = [
            command
            for command in commands
            if command.data.get("finger") == finger
            and command.data.get("pressed", False)
            and command.timestamp_ns >= t0_ns
            and command.timestamp_ns <= event.timestamp_ns
        ]
        if candidates:
            onset = candidates[-1].timestamp_ns
            latency[finger] = max(0.0, (event.timestamp_ns - onset) / 1_000_000_000)
    return latency


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """Calculate Pearson correlation when at least two nonconstant paired values exist."""
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True))
    x_norm = math.sqrt(sum((x - x_mean) ** 2 for x in xs))
    y_norm = math.sqrt(sum((y - y_mean) ** 2 for y in ys))
    if x_norm == 0 or y_norm == 0:
        return None
    return numerator / (x_norm * y_norm)


def score_trial(task: str, events: list[Event], t0_ns: int) -> Score:
    """Score a trial using only its recorded event stream."""
    if task not in TASKS:
        raise ValueError(f"Unknown DexBench task: {task}")
    invalid = next((event for event in events if event.topic == "/dexbench/invalid"), None)
    if invalid is not None:
        return Score(False, str(invalid.data.get("reason", "hardware_fault")), {}, True)
    if task == "keypress-ldr":
        return _score_keypress(events, t0_ns)
    if task == "piano-seq":
        return _score_piano(events, t0_ns)
    return _score_pick_place(events, t0_ns)


def _score_keypress(events: list[Event], t0_ns: int) -> Score:
    """Score the hardware-grounded arrow-key sequence."""
    end_ns = t0_ns + 10_000_000_000
    observed = [
        event
        for event in _select(events, "/keyboard/events")
        if t0_ns <= event.timestamp_ns <= end_ns
        and event.data.get("kind") == "key_down"
        and event.data.get("repeat") is not True
        and event.data.get("is_repeat") is not True
        and event.data.get("value") != 2
    ]
    keys = [str(event.data.get("key", "")).upper() for event in observed]
    target = ["LEFT", "DOWN", "RIGHT"]
    success = keys == target
    completed_ns = observed[2].timestamp_ns if len(observed) >= 3 and success else None
    reason = "success" if success else _sequence_failure(keys, target, end_ns, events, t0_ns)
    return Score(
        success,
        reason,
        {
            "completion_time_s": _completion(events, t0_ns, completed_ns),
            "per_finger_latency_s": _latencies(events, t0_ns, observed[:3]),
            "key_events": keys,
        },
    )


def _score_piano(events: list[Event], t0_ns: int) -> Score:
    """Score the note sequence and report velocity and tactile measurements."""
    end_ns = t0_ns + 10_000_000_000
    notes = [
        event
        for event in _select(events, "/midi/events")
        if t0_ns <= event.timestamp_ns <= end_ns and event.data.get("kind") == "note_on"
    ]
    sequence = [int(event.data.get("note", -1)) for event in notes]
    velocities = [int(event.data.get("velocity", 0)) for event in notes]
    sequence_ok = sequence == [60, 62, 64]
    success = sequence_ok
    tactile = [
        event for event in _select(events, "/hand/tactile") if t0_ns <= event.timestamp_ns <= end_ns
    ]
    force_values: list[float] = []
    paired_velocities: list[float] = []
    for note in notes:
        nearest = min(
            tactile,
            key=lambda sample: abs(sample.timestamp_ns - note.timestamp_ns),
            default=None,
        )
        if nearest is not None and "force_n" in nearest.data:
            force_values.append(float(nearest.data["force_n"]))
            paired_velocities.append(float(note.data.get("velocity", 0)))
    timed_out = any(event.topic == "/dexbench/timeout" for event in events)
    reason = "success" if success else "timeout" if timed_out else "note_sequence_incorrect"
    return Score(
        success,
        reason,
        {
            "completion_time_s": _completion(
                events, t0_ns, notes[-1].timestamp_ns if sequence_ok else None
            ),
            "per_finger_latency_s": {
                "index": _command_latency(events, "index", notes, 0, t0_ns),
                "middle": _command_latency(events, "middle", notes, 1, t0_ns),
                "ring": _command_latency(events, "ring", notes, 2, t0_ns),
            },
            "notes": sequence,
            "velocities": velocities,
            "within_trial_velocity_stddev": _stddev(velocities),
            "medium_velocity_hit_rate": (
                sum(50 <= velocity <= 90 for velocity in velocities) / len(velocities)
                if velocities
                else None
            ),
            "tactile_velocity_correlation": _pearson(force_values, paired_velocities),
        },
    )


def _command_latency(
    events: list[Event], finger: str, target_events: list[Event], target_index: int, t0_ns: int
) -> float | None:
    """Return one finger's command-to-contact latency."""
    if len(target_events) <= target_index:
        return None
    target = target_events[target_index]
    commands = [
        event
        for event in _select(events, "/hand/command")
        if event.data.get("finger") == finger
        and event.data.get("pressed", False)
        and event.timestamp_ns >= t0_ns
        and event.timestamp_ns <= target.timestamp_ns
    ]
    if not commands:
        return None
    return max(0.0, (target.timestamp_ns - commands[-1].timestamp_ns) / 1_000_000_000)


def _stddev(values: list[int]) -> float | None:
    """Return population standard deviation for a nonempty list."""
    if not values:
        return None
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _score_pick_place(events: list[Event], t0_ns: int) -> Score:
    """Score release, tray placement, and one second of observed stability."""
    end_ns = t0_ns + 60_000_000_000
    tray_events = [
        event
        for event in _select(events, "/scorer/tray_state")
        if t0_ns <= event.timestamp_ns <= end_ns
    ]
    releases = [
        event
        for event in _select(events, "/hand/state")
        if t0_ns <= event.timestamp_ns <= end_ns and event.data.get("open", False)
    ]
    successful_tray = None
    inside_since_ns = None
    for event in tray_events:
        if not event.data.get("object_inside", False):
            inside_since_ns = None
            continue
        if inside_since_ns is None:
            inside_since_ns = event.timestamp_ns
        if float(event.data.get("stable_duration_s", 0.0)) >= 1.0 and any(
            inside_since_ns <= release.timestamp_ns <= event.timestamp_ns for release in releases
        ):
            successful_tray = event
            break
    success = successful_tray is not None
    reason = (
        "success"
        if success
        else "timeout"
        if any(event.topic == "/dexbench/timeout" for event in events)
        else "not_placed"
    )
    return Score(
        success,
        reason,
        {
            "completion_time_s": _completion(
                events, t0_ns, successful_tray.timestamp_ns if successful_tray else None
            )
        },
    )


def _sequence_failure(
    actual: list[str], expected: list[str], end_ns: int, events: list[Event], t0_ns: int
) -> str:
    """Explain a failed keyboard sequence from the observed events."""
    if any(event.timestamp_ns > end_ns for event in _select(events, "/keyboard/events")):
        return "timeout"
    if actual and actual != expected[: len(actual)]:
        return "wrong_or_extra_key"
    if len(actual) >= len(expected):
        return "wrong_or_extra_key"
    if any(event.topic == "/dexbench/timeout" for event in events):
        return "timeout"
    if not actual and max((event.timestamp_ns for event in events), default=t0_ns) >= end_ns:
        return "timeout"
    return "incomplete_sequence"

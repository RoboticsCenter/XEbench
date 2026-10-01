"""No-physics mock adapter and dynamic loading for user-supplied robot adapters."""

from __future__ import annotations

import importlib
import time
from typing import Any

from xebench.models import Action, Event, Observation
from xebench.tasks import FINGER_FOR_KEY, INSTRUCTIONS


class MockKeyboardAdapter:
    """A no-physics event simulator for trying the keypress CLI and result format."""

    name = "mock-keyboard"

    def __init__(self) -> None:
        """Initialize an empty mock trial."""
        self._events: list[Event] = []
        self._t0_ns = 0
        self._step = 0

    def reset(self, task: str, trial_id: str, metadata: dict[str, Any]) -> int:
        """Start a mock trial and return its monotonic start timestamp."""
        del trial_id, metadata
        if task != "keypress-ldr":
            raise ValueError("The included mock adapter currently supports keypress-ldr only")
        self._events = []
        self._step = 0
        self._t0_ns = time.monotonic_ns()
        return self._t0_ns

    def observe(self) -> tuple[int, list[Event]]:
        """Return the current mock timestamp and no new events."""
        return time.monotonic_ns(), []

    def execute(self, action: Action) -> list[Event]:
        """Translate a bounded finger press into mock command and keyboard events."""
        if action.kind != "press" or action.parameters.get("finger") not in FINGER_FOR_KEY.values():
            raise ValueError(f"Unsupported mock action: {action.to_dict()!r}")
        self._step += 1
        command_ns = time.monotonic_ns()
        finger = str(action.parameters["finger"])
        key = next((target for target, name in FINGER_FOR_KEY.items() if name == finger), "")
        emitted = [
            Event(
                "/hand/command",
                command_ns,
                {"finger": finger, "pressed": True, "source": "mock"},
            )
        ]
        time.sleep(0.025)
        emitted.append(
            Event(
                "/keyboard/events",
                time.monotonic_ns(),
                {"kind": "key_down", "key": key, "source": "mock"},
            )
        )
        self._events.extend(emitted)
        return emitted

    def close(self) -> None:
        """Release resources (none for this mock)."""


def load_adapter(spec: str, session_metadata: dict[str, Any]):
    """Load an adapter factory from a Python ``module:attribute`` reference."""
    module_name, separator, attribute_name = spec.partition(":")
    if not separator:
        raise ValueError(
            "Adapter must be 'mock' or a Python reference such as package.module:factory"
        )
    module = importlib.import_module(module_name)
    factory = getattr(module, attribute_name)
    return factory(session_metadata)


def create_observation(
    task: str,
    t0_ns: int,
    now_ns: int,
    events: list[Event],
    metadata: dict[str, Any],
) -> Observation:
    """Build the task-scoped policy observation from adapter events."""
    return Observation(task, INSTRUCTIONS[task], t0_ns, now_ns, tuple(events), metadata)

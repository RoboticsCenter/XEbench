"""Shared data structures and adapter contracts for XEbench."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Event:
    """One timestamped observation or command from a benchmark run."""

    topic: str
    timestamp_ns: int
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible event record."""
        return asdict(self)


@dataclass(frozen=True)
class Action:
    """A policy request expressed in the benchmark's robot-independent action space."""

    kind: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible action record."""
        return asdict(self)


@dataclass(frozen=True)
class Observation:
    """The task instruction and recorded sensor state visible to a policy."""

    task: str
    instruction: str
    t0_ns: int
    now_ns: int
    events: tuple[Event, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Score:
    """A task score and its measurable outcome fields."""

    success: bool
    reason: str
    metrics: dict[str, Any] = field(default_factory=dict)
    invalid: bool = False


class Policy(Protocol):
    """Interface implemented by scripted, learned, replay, or operator policies."""

    name: str

    def reset(self, task: str, trial_id: str) -> None:
        """Reset policy state before a trial."""

    def act(self, observation: Observation) -> Action | None:
        """Return one action, or None to finish the trial."""


class Adapter(Protocol):
    """Bridge between XEbench and a simulator or physical robot."""

    name: str

    def reset(self, task: str, trial_id: str, metadata: dict[str, Any]) -> int:
        """Prepare a trial and return the monotonic start timestamp in nanoseconds."""

    def observe(self) -> tuple[int, list[Event]]:
        """Return the current monotonic timestamp and newly available sensor events."""

    def execute(self, action: Action) -> list[Event]:
        """Execute one bounded action and return sensor/command events it produced."""

    def close(self) -> None:
        """Release adapter resources after the run."""

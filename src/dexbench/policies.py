"""Reference policies: an offline scripted policy and an OpenAI-compatible LLM agent."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from dexbench.models import Action, Adapter, Observation
from dexbench.recording import read_mcap_events
from dexbench.tasks import FINGER_FOR_KEY, TASKS


class ScriptedKeyboardPolicy:
    """Deterministic example policy for exercising the keyboard evaluation path."""

    name = "scripted"

    def reset(self, task: str, trial_id: str) -> None:
        """Reset the next target key for a new trial."""
        del trial_id
        if task != "keypress-ldr":
            raise ValueError("The included scripted policy currently supports keypress-ldr only")
        self._next_index = 0

    def act(self, observation: Observation) -> Action | None:
        """Request the next key press until all three target events are visible."""
        keys = [
            str(event.data.get("key", "")).upper()
            for event in observation.events
            if event.topic == "/keyboard/events" and event.data.get("kind") == "key_down"
        ]
        sequence = TASKS["keypress-ldr"]["sequence"]
        self._next_index = min(len(keys), len(sequence))
        if self._next_index >= len(sequence):
            return None
        key = sequence[self._next_index]
        return Action("press", {"finger": FINGER_FOR_KEY[key]})


class OpenAICompatiblePolicy:
    """Call an OpenAI Chat Completions-compatible endpoint for bounded key actions."""

    name = "llm"

    def __init__(self) -> None:
        """Read endpoint, credential, and model from environment variables."""
        self.base_url = os.environ.get("DEXBENCH_LLM_BASE_URL", "https://api.openai.com/v1")
        self.api_key = os.environ.get("DEXBENCH_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("DEXBENCH_LLM_MODEL", "gpt-4.1-mini")
        self.last_trace: dict[str, Any] = {}
        if not self.api_key:
            raise ValueError(
                "Set DEXBENCH_LLM_API_KEY (or OPENAI_API_KEY) to use the example LLM policy"
            )

    def reset(self, task: str, trial_id: str) -> None:
        """Validate task scope and clear the prior model call trace."""
        del trial_id
        if task != "keypress-ldr":
            raise ValueError("The included LLM policy currently supports keypress-ldr only")
        self.last_trace = {}

    def act(self, observation: Observation) -> Action | None:
        """Ask the model for one finger press and validate its structured response."""
        visible = [
            event.to_dict()
            for event in observation.events
            if event.topic in {"/keyboard/events", "/hand/state", "/hand/tactile"}
        ]
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You control a dexterous hand using exactly one bounded action per turn. "
                        "Follow the task instruction and the visible event history. Reply only as "
                        'JSON: {"action":"press","finger":"index|middle|ring"} or '
                        '{"action":"stop"}. Never invent sensor readings. Do not output robot '
                        "joint commands."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": observation.task,
                            "instruction": observation.instruction,
                            "elapsed_s": round((observation.now_ns - observation.t0_ns) / 1e9, 3),
                            "events": visible,
                        },
                        separators=(",", ":"),
                    ),
                },
            ],
        }
        response = httpx.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        result = json.loads(content)
        self.last_trace = {
            "model": self.model,
            "response_id": body.get("id"),
            "request": payload,
            "response": result,
        }
        if result.get("action") == "stop":
            return None
        if result.get("action") != "press" or result.get("finger") not in {
            "index",
            "middle",
            "ring",
        }:
            raise ValueError(f"LLM response is outside the allowed action space: {result!r}")
        return Action("press", {"finger": result["finger"]})


class ReplayPolicy:
    """Replay original hand/arm command events from one recorded MCAP trial."""

    name = "replay"

    def __init__(self, source_mcap: str, topics: list[str]) -> None:
        """Read the command stream to replay, preserving source timing."""
        self.source_mcap = source_mcap
        self.topics = set(topics)
        all_events = read_mcap_events(Path(source_mcap))
        self._source = [event for event in all_events if event.topic in self.topics]
        if not self._source:
            raise ValueError(f"No replayable command topics {sorted(self.topics)} in {source_mcap}")
        trial = next(
            (
                event
                for event in all_events
                if event.topic == "/dexbench/trial" and event.data.get("t0")
            ),
            None,
        )
        self.source_trial_id = str(trial.data.get("trial_id", "")) if trial else ""

    def reset(self, task: str, trial_id: str) -> None:
        """Reset the source command cursor for a run."""
        del task, trial_id
        self._index = 0
        self._replay_t0_ns: int | None = None
        self._source_t0_ns = self._source[0].timestamp_ns

    def act(self, observation: Observation) -> Action | None:
        """Wait for each source event's relative time, then dispatch it to the adapter."""
        if self._index >= len(self._source):
            return None
        if self._replay_t0_ns is None:
            self._replay_t0_ns = observation.now_ns
        event = self._source[self._index]
        target_ns = self._replay_t0_ns + (event.timestamp_ns - self._source_t0_ns)
        delay_s = (target_ns - time.monotonic_ns()) / 1_000_000_000
        if delay_s > 0:
            time.sleep(delay_s)
        self._index += 1
        return Action("replay_command", {"topic": event.topic, "data": event.data})


class TeleopPolicy:
    """Use an adapter-provided operator input source for a teleoperation baseline."""

    name = "teleop"

    def __init__(self) -> None:
        """Initialize without choosing a robot-specific input source."""
        self._adapter: Adapter | None = None

    def bind_adapter(self, adapter: Adapter) -> None:
        """Bind the active adapter, which must expose a ``teleop_action`` method."""
        self._adapter = adapter

    def reset(self, task: str, trial_id: str) -> None:
        """Reset the bound operator control source when it supports reset."""
        del task, trial_id
        if self._adapter is None or not hasattr(self._adapter, "teleop_action"):
            raise ValueError("Teleop requires an adapter with a teleop_action(observation) method")
        reset = getattr(self._adapter, "reset_teleop", None)
        if callable(reset):
            reset()

    def act(self, observation: Observation) -> Action | None:
        """Read one bounded operator action from the active adapter."""
        if self._adapter is None:
            raise ValueError("Teleop policy is not bound to an adapter")
        teleop_action = getattr(self._adapter, "teleop_action", None)
        if not callable(teleop_action):
            raise ValueError("Bound adapter does not implement teleop_action(observation)")
        action = teleop_action(observation)
        if action is not None and not isinstance(action, Action):
            raise TypeError("Adapter teleop_action must return Action or None")
        return action

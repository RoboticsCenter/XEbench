"""MCAP serialization and summary helpers."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from mcap.reader import make_reader
from mcap.writer import Writer

from xebench.models import Event

JSON_SCHEMA = {
    "type": "object",
    "required": ["topic", "timestamp_ns", "data"],
    "properties": {
        "topic": {"type": "string"},
        "timestamp_ns": {"type": "integer"},
        "data": {"type": "object"},
    },
}


def write_mcap(path: Path, events: list[Event], metadata: dict[str, Any]) -> None:
    """Write timestamped JSON event channels and run metadata to one MCAP file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        writer = Writer(stream)
        writer.start(profile="dexbench", library="rc-dexbench/0.1.0")
        schema_id = writer.register_schema(
            name="dexbench.Event",
            encoding="jsonschema",
            data=json.dumps(JSON_SCHEMA, separators=(",", ":")).encode(),
        )
        channels: dict[str, int] = {}
        counts: defaultdict[str, int] = defaultdict(int)
        writer.add_metadata("dexbench.run", {str(k): json.dumps(v) for k, v in metadata.items()})
        for event in sorted(events, key=lambda item: item.timestamp_ns):
            if event.topic not in channels:
                channels[event.topic] = writer.register_channel(
                    topic=event.topic,
                    message_encoding="json",
                    schema_id=schema_id,
                    metadata={"dexbench.event_format": "Event v1"},
                )
            writer.add_message(
                channel_id=channels[event.topic],
                log_time=event.timestamp_ns,
                publish_time=event.timestamp_ns,
                sequence=counts[event.topic],
                data=json.dumps(event.to_dict(), separators=(",", ":")).encode(),
            )
            counts[event.topic] += 1
        writer.finish()


def read_mcap_events(path: Path) -> list[Event]:
    """Read XEbench JSON events from an MCAP file."""
    events = []
    with path.open("rb") as stream:
        reader = make_reader(stream)
        for _schema, _channel, message in reader.iter_messages():
            value = json.loads(message.data)
            if {"topic", "timestamp_ns", "data"} <= value.keys():
                events.append(Event(value["topic"], int(value["timestamp_ns"]), value["data"]))
    return sorted(events, key=lambda event: event.timestamp_ns)


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write a formatted UTF-8 JSON summary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

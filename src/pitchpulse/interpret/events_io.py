"""Load match event streams from disk."""

from __future__ import annotations

from pitchpulse.data.paths import match_dir
from pitchpulse.schema.events import MatchEvent


def load_events(match_id: str) -> list[MatchEvent]:
    path = match_dir(match_id) / "events.jsonl"
    events: list[MatchEvent] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(MatchEvent.from_json_line(line))
    return events

"""Validate generated match bundles."""

from __future__ import annotations

import argparse
import json
import sys

from pitchpulse.data.paths import match_dir
from pitchpulse.schema.events import MatchEvent


def validate(match_id: str) -> int:
    mdir = match_dir(match_id)
    events_path = mdir / "events.jsonl"
    if not events_path.exists():
        print(f"Missing {events_path}", file=sys.stderr)
        return 1

    prev_t = -1
    ids: set[str] = set()
    count = 0
    with events_path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                ev = MatchEvent.from_json_line(line)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"Line {line_no}: {e}", file=sys.stderr)
                return 1
            if ev.t_ms < prev_t:
                print(f"Line {line_no}: t_ms not monotonic ({ev.t_ms} < {prev_t})", file=sys.stderr)
                return 1
            prev_t = ev.t_ms
            if ev.event_id in ids:
                print(f"Duplicate event_id {ev.event_id}", file=sys.stderr)
                return 1
            ids.add(ev.event_id)
            count += 1

    manifest = json.loads((mdir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("event_count") != count:
        print(f"manifest event_count {manifest.get('event_count')} != actual {count}", file=sys.stderr)
        return 1

    required = [
        "expected_alerts.json",
        "substitution_moments.json",
        "minute_snapshots.json",
        "player_match_rollups.json",
        "lineups.json",
        "meta.json",
    ]
    for name in required:
        if not (mdir / name).exists():
            print(f"Missing {mdir / name}", file=sys.stderr)
            return 1

    print(f"OK: {match_id} — {count} events validated")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--match", default="syn-001")
    args = parser.parse_args()
    raise SystemExit(validate(args.match))


if __name__ == "__main__":
    main()

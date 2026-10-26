"""Verify fired alerts align with expected_alerts.json for the demo match."""

from __future__ import annotations

import argparse
import json
import sys

from pitchpulse.data.paths import match_dir
from pitchpulse.interpret.engine import replay_alerts
from pitchpulse.interpret.events_io import load_events


def assert_demo(match_id: str, tolerance_ms: int = 90_000) -> int:
    expected_path = match_dir(match_id) / "expected_alerts.json"
    if not expected_path.exists():
        print(f"Missing {expected_path}", file=sys.stderr)
        return 1

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    events = load_events(match_id)
    _, fired = replay_alerts(events, match_id=match_id)

    fired_by_id: dict[str, list] = {}
    for alert in fired:
        fired_by_id.setdefault(alert.alert_id, []).append(alert)

    ok = True
    for exp in expected:
        aid = exp["alert_id"]
        t0 = int(exp["t_start_ms"]) - tolerance_ms
        t1 = int(exp["t_end_ms"]) + tolerance_ms
        candidates = fired_by_id.get(aid, [])
        in_window = [a for a in candidates if t0 <= a.t_ms <= t1]
        if not in_window:
            ok = False
            print(
                f"FAIL: {aid} — no fire between {t0}–{t1} ms "
                f"(fires: {[a.t_ms for a in candidates]})",
                file=sys.stderr,
            )
        else:
            best = min(in_window, key=lambda a: abs(a.t_ms - int(exp["t_peak_ms"])))
            print(
                f"OK: {aid} at {best.match_minute:.1f}' (t_ms={best.t_ms}) "
                f"evidence={ {k: best.evidence[k] for k in list(best.evidence)[:4]} }..."
            )

    extra = set(fired_by_id.keys()) - {e["alert_id"] for e in expected}
    if extra:
        print(f"Note: additional alert ids fired (not in expected): {sorted(extra)}")

    if ok:
        print(f"All {len(expected)} expected demo alerts verified for {match_id}.")
        return 0
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Assert demo alerts against expected_alerts.json")
    parser.add_argument("--match", default="syn-001")
    parser.add_argument("--tolerance-ms", type=int, default=90_000)
    args = parser.parse_args()
    raise SystemExit(assert_demo(args.match, tolerance_ms=args.tolerance_ms))


if __name__ == "__main__":
    main()

"""CLI: compile story beats into a full synthetic match bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from random import Random

from pitchpulse.data import beats, filler
from pitchpulse.data.emitters import EventFactory
from pitchpulse.data.paths import DATA_DIR, match_dir, storybeat_path
from pitchpulse.data.pitch import ms_from_minute
from pitchpulse.data.post_sub import emit_flank_recovery, emit_mid_recovery
from pitchpulse.data.snapshots import (
    build_minute_snapshots,
    build_player_rollups,
    window_metrics,
)
from pitchpulse.schema.events import ExpectedAlert, MatchEvent, SubstitutionMoment


def load_storybeats(match_id: str) -> dict:
    json_path = DATA_DIR / "storybeats" / f"{match_id}.json"
    yaml_path = storybeat_path(match_id)
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    if yaml_path.exists():
        try:
            import yaml
        except ImportError as e:
            raise ImportError(
                f"Install pyyaml or add {json_path} (JSON storybeats mirror)."
            ) from e
        with yaml_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)
    raise FileNotFoundError(f"Missing storybeats: {json_path} or {yaml_path}")


def dispatch_beat(
    factory: EventFactory,
    rng: Random,
    beat: dict,
    roster: dict,
) -> list[MatchEvent]:
    kind = beat["kind"]
    period = int(beat.get("period", 1))
    t0, t1 = beats.beat_window_ms(beat, period)
    actors = beat.get("actors", {})

    if kind == "flank_overload_right":
        return beats.emit_beat_flank_overload(
            factory,
            rng,
            period,
            t0,
            t1,
            attacking_team=actors.get("attacking_team", "home"),
            crossing_player=actors["crossing_player"],
            exposed_defender=actors["exposed_defender"],
            dominant_attacker=actors["dominant_attacker"],
        )
    if kind == "midfield_chaos":
        return beats.emit_beat_midfield_chaos(
            factory,
            rng,
            period,
            t0,
            t1,
            pressing_team=actors.get("pressing_team", "home"),
            exposed_mid=actors["exposed_mid"],
            presser=actors["presser"],
        )
    if kind == "shot_speed_spike":
        return beats.emit_beat_shot_spike(
            factory,
            rng,
            period,
            t0,
            t1,
            team_id=actors.get("team", "home"),
            shooter=actors["shooter"],
        )
    if kind == "low_defensive_contacts":
        return beats.emit_beat_low_defensive_contacts(
            factory,
            rng,
            period,
            t0,
            t1,
            defending_team=actors.get("defending_team", "away"),
            weak_cb=actors["weak_cb"],
            attacker=actors["attacker"],
        )
    if kind == "unproductive_crosses":
        return beats.emit_beat_unproductive_crosses(
            factory,
            rng,
            period,
            t0,
            t1,
            team_id=actors.get("team", "home"),
            crossing_player=actors["crossing_player"],
        )
    if kind == "wasteful_finishing":
        return beats.emit_beat_wasteful_finishing(
            factory,
            rng,
            period,
            t0,
            t1,
            team_id=actors.get("team", "home"),
            shooter=actors["shooter"],
        )
    if kind == "midfield_link_break":
        return beats.emit_beat_midfield_link_break(
            factory,
            rng,
            period,
            t0,
            t1,
            team_id=actors.get("team", "away"),
            passer=actors["passer"],
        )
    if kind == "player_focus":
        return beats.emit_beat_player_focus(
            factory,
            rng,
            period,
            t0,
            t1,
            team_id=actors.get("team", "home"),
            player_id=actors["player_id"],
        )
    raise ValueError(f"Unknown beat kind: {kind}")


def build_expected_alerts(story: dict) -> list[ExpectedAlert]:
    out: list[ExpectedAlert] = []
    for b in story.get("expected_alerts", []):
        period = int(b.get("period", 1))
        t0 = ms_from_minute(float(b["minute_start"]), period)
        t_peak = ms_from_minute(float(b["minute_peak"]), period)
        t1 = ms_from_minute(float(b["minute_end"]), period)
        out.append(
            ExpectedAlert(
                alert_id=b["alert_id"],
                t_start_ms=t0,
                t_peak_ms=t_peak,
                t_end_ms=t1,
                storyline=b["storyline"],
                audience_primary=b.get("audience_primary", ["coach", "analyst"]),
                leak_summary=b["leak_summary"],
                coach_gap=b["coach_gap"],
                related_player_ids=b.get("related_player_ids", []),
            )
        )
    return out


def build_substitution_moments(story: dict, events: list[MatchEvent]) -> list[SubstitutionMoment]:
    moments: list[SubstitutionMoment] = []
    for sub in story.get("substitutions", []):
        period = int(sub.get("period", 2))
        t_sub = ms_from_minute(float(sub["minute"]), period)
        pre = int(sub.get("fan_window_before_ms", 5 * 60 * 1000))
        post = int(sub.get("fan_window_after_ms", 10 * 60 * 1000))
        t0 = t_sub - pre
        t1 = t_sub + post
        fb_before = sub["player_off"]
        fb_after = sub["player_on"]
        pivot_before = sub["player_off"]
        pivot_after = sub["player_on"]
        if sub["addresses_alert_id"] == "flank_overload_right":
            before = window_metrics(events, t0, t_sub - 1, fullback_id=fb_before)
            after = window_metrics(events, t_sub, t1, fullback_id=fb_after)
        else:
            before = window_metrics(events, t0, t_sub - 1, pivot_id=pivot_before)
            after = window_metrics(events, t_sub, t1, pivot_id=pivot_after)
        moments.append(
            SubstitutionMoment(
                moment_id=sub["moment_id"],
                t_sub_ms=t_sub,
                team_id=sub["team_id"],
                player_off_id=sub["player_off"],
                player_on_id=sub["player_on"],
                addresses_alert_id=sub["addresses_alert_id"],
                fan_window_start_ms=t0,
                fan_window_end_ms=t1,
                narrative_hook=sub["narrative_hook"],
                metrics_before=before,
                metrics_after=after,
                observable_outcome=sub["observable_outcome"],
            )
        )
    return moments


def generate(match_id: str, seed: int = 42) -> Path:
    story = load_storybeats(match_id)
    rng = Random(seed)
    factory = EventFactory(match_id, rng)

    events: list[MatchEvent] = []
    events.append(factory.meta(0, 1, "kickoff", meta={"label": "kickoff"}))

    home_mids = story["lineups"]["home"]["midfielders"]
    away_mids = story["lineups"]["away"]["midfielders"]
    # Include GKs so keepers get build-up passes; outfield still dominate via sampling.
    home_pool = [p["id"] for p in story["lineups"]["home"]["starters"]] or home_mids
    away_pool = [p["id"] for p in story["lineups"]["away"]["starters"]] or away_mids
    cursor = ms_from_minute(0.5, 1)

    all_beats = sorted(
        story["beats"],
        key=lambda b: (int(b.get("period", 1)), float(b["minute_start"])),
    )
    p1_beats = [b for b in all_beats if int(b.get("period", 1)) == 1]
    p2_beats = [b for b in all_beats if int(b.get("period", 1)) == 2]

    for beat in p1_beats:
        period = 1
        t0, t1 = beats.beat_window_ms(beat, period)
        if cursor < t0:
            filler_events, cursor = filler.fill_gaps(
                factory, rng, period, cursor, t0, home_pool, away_pool
            )
            events.extend(filler_events)
        events.extend(dispatch_beat(factory, rng, beat, story))
        cursor = max(cursor, t1)

    ht_ms = ms_from_minute(45, 1)
    if cursor < ht_ms - 30_000:
        filler_events, cursor = filler.fill_gaps(
            factory, rng, 1, cursor, ht_ms - 30_000, home_pool, away_pool
        )
        events.extend(filler_events)

    events.append(factory.meta(ht_ms, 1, "half_time", meta={"label": "half_time"}))
    events.append(factory.meta(ht_ms + 1000, 2, "second_half_kickoff", meta={"label": "second_half_kickoff"}))

    cursor_p2 = ms_from_minute(46)
    for beat in p2_beats:
        period = 2
        t0, t1 = beats.beat_window_ms(beat, period)
        if cursor_p2 < t0:
            filler_events, cursor_p2 = filler.fill_gaps(
                factory, rng, period, cursor_p2, t0, home_pool, away_pool
            )
            events.extend(filler_events)
        events.extend(dispatch_beat(factory, rng, beat, story))
        cursor_p2 = max(cursor_p2, t1)

    recovery_events: list[MatchEvent] = []
    for sub in story.get("substitutions", []):
        period = int(sub.get("period", 2))
        t_sub = ms_from_minute(float(sub["minute"]), period)
        events.append(
            factory.substitution(
                t_sub,
                period,
                sub["team_id"],
                sub["player_off"],
                sub["player_on"],
                sub["addresses_alert_id"],
            )
        )
        post_ms = int(sub.get("fan_window_after_ms", 10 * 60 * 1000))
        if sub["moment_id"] == "sub_flank_fix":
            recovery_events.extend(
                emit_flank_recovery(
                    factory, rng, t_sub, t_sub + post_ms, sub["team_id"], sub["player_on"]
                )
            )
        if sub["moment_id"] == "sub_mid_fix":
            recovery_events.extend(
                emit_mid_recovery(factory, rng, t_sub, t_sub + post_ms, sub["player_on"])
            )
    events.extend(recovery_events)

    ft_ms = ms_from_minute(90, 2)
    events.append(factory.meta(ft_ms, 2, "full_time", meta={"label": "full_time", "score": story["meta"]["final_score"]}))

    filler_tail, _ = filler.fill_gaps(
        factory, rng, 2, cursor_p2, ft_ms - 60_000, home_pool, away_pool
    )
    events.extend(filler_tail)

    events.sort(key=lambda e: (e.t_ms, e.event_id))

    out_dir = match_dir(match_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    with (out_dir / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(story["meta"], f, indent=2)
    with (out_dir / "lineups.json").open("w", encoding="utf-8") as f:
        json.dump(story["lineups"], f, indent=2)

    with (out_dir / "events.jsonl").open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(ev.to_json_line() + "\n")

    expected = build_expected_alerts(story)
    with (out_dir / "expected_alerts.json").open("w", encoding="utf-8") as f:
        json.dump([a.__dict__ for a in expected], f, indent=2)

    subs = build_substitution_moments(story, events)
    with (out_dir / "substitution_moments.json").open("w", encoding="utf-8") as f:
        json.dump([s.__dict__ for s in subs], f, indent=2)

    snapshots = build_minute_snapshots(events)
    with (out_dir / "minute_snapshots.json").open("w", encoding="utf-8") as f:
        json.dump(snapshots, f, indent=2)

    rollups = build_player_rollups(events)
    with (out_dir / "player_match_rollups.json").open("w", encoding="utf-8") as f:
        json.dump(rollups, f, indent=2)

    manifest = {
        "match_id": match_id,
        "event_count": len(events),
        "seed": seed,
        "storybeat_file": str(storybeat_path(match_id).relative_to(out_dir.parent.parent)),
    }
    with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic PitchPulse match dataset")
    parser.add_argument("--match", default="syn-001", help="Match id (data/storybeats/{id}.yaml)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    out = generate(args.match, seed=args.seed)
    print(f"Generated {out} ({(out / 'manifest.json').read_text()})")


if __name__ == "__main__":
    main()

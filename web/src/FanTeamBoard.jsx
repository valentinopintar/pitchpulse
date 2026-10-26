import { useEffect, useMemo, useState } from "react";

function CrowdCallHero({ calls, side, liveLabel, onExplain }) {
  const list = calls || [];
  return (
    <div
      className={`crowd-hero side-${side}`}
      data-explain="crowdCard"
      onClick={(e) => {
        e.stopPropagation();
        onExplain?.("crowdCard", e.currentTarget);
      }}
    >
      <div className="crowd-hero-head">
        <span className="crowd-kicker">Crowd call{liveLabel ? " · live" : ""}</span>
        <h3>What are the fans saying?</h3>
        <p>
          {liveLabel
            ? `Opinions for ${liveLabel} — updates every 5' with the match clock.`
            : "Positive and negative takes from the stands — the heart of PitchPulse."}
        </p>
      </div>
      {list.length === 0 ? (
        <p className="status-line">Load the match to unlock crowd calls.</p>
      ) : (
        <div className="crowd-call-list">
          {list.map((c) => (
            <article
              key={c.id}
              className={`crowd-call-row polarity-${c.polarity || "negative"}`}
            >
              <div className="crowd-call-q">
                <strong>{c.question}</strong>
                <span className={`badge ${c.polarity === "positive" ? "good" : ""}`}>
                  {c.polarity === "positive" ? "boost" : "pressure"}
                </span>
              </div>
              <div className="crowd-bar tall">
                <span
                  className={c.polarity === "positive" ? "pos" : ""}
                  style={{ width: `${c.fan_pct}%` }}
                />
              </div>
              <div className="crowd-call-meta">
                <span className={`crowd-pct ${c.polarity === "positive" ? "pos" : ""}`}>
                  {c.fan_pct}%
                </span>
                <span>{c.blurb}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function SliceScrubber({ slices, activeIdx, onChange, liveIdx }) {
  const total = slices?.length || 0;
  if (!total) return null;

  const prevIdx = activeIdx > 0 ? activeIdx - 1 : null;
  const nextIdx = activeIdx < total - 1 ? activeIdx + 1 : null;
  const cells = [
    { idx: prevIdx, role: "prev" },
    { idx: activeIdx, role: "current" },
    { idx: nextIdx, role: "next" },
  ];

  return (
    <div className="slice-nav" aria-label="Five-minute windows">
      <button
        type="button"
        className="slice-arrow"
        disabled={prevIdx == null}
        aria-label="Previous 5 minutes"
        onClick={(e) => {
          e.stopPropagation();
          if (prevIdx != null) onChange(prevIdx);
        }}
      >
        ‹ Prev
      </button>
      <div className="slice-trio">
        {cells.map((cell) => {
          const s = cell.idx != null ? slices[cell.idx] : null;
          if (!s) {
            return (
              <div key={cell.role} className={`slice-cell empty role-${cell.role}`}>
                —
              </div>
            );
          }
          const isActive = cell.idx === activeIdx;
          const isLive = cell.idx === liveIdx;
          return (
            <button
              key={cell.role}
              type="button"
              className={`slice-cell role-${cell.role} ${isActive ? "active" : ""} ${
                isLive ? "live-tick" : ""
              }`}
              onClick={(e) => {
                e.stopPropagation();
                onChange(cell.idx);
              }}
            >
              <span className="slice-cell-label">{s.label}</span>
              {isLive ? <span className="slice-cell-live">live</span> : null}
            </button>
          );
        })}
      </div>
      <button
        type="button"
        className="slice-arrow"
        disabled={nextIdx == null}
        aria-label="Next 5 minutes"
        onClick={(e) => {
          e.stopPropagation();
          if (nextIdx != null) onChange(nextIdx);
        }}
      >
        Next ›
      </button>
    </div>
  );
}

function OpinionBars({ negative, positive, windowLabel }) {
  return (
    <div className="opinion-grid">
      <div className="chart-block under-block">
        <h3>Under pressure · {windowLabel}</h3>
        <p className="chart-caption">Fans who think these players were off it.</p>
        <div className="bar-chart">
          {(negative || []).length === 0 ? (
            <p className="status-line">No clear negatives in this window.</p>
          ) : (
            negative.map((r) => (
              <div className="bar-row" key={`n-${r.player_id}`}>
                <div className="bar-label">
                  <span className="bar-shirt">#{r.shirt}</span>
                  <span>{r.name}</span>
                </div>
                <div className="bar-track">
                  <span
                    className="bar-fill warn"
                    style={{ width: `${Math.max(8, r.fan_disapproval_pct ?? r.fan_pct)}%` }}
                  />
                </div>
                <div className="bar-value">{r.fan_disapproval_pct ?? r.fan_pct}%</div>
              </div>
            ))
          )}
        </div>
      </div>
      <div className="chart-block under-block pos-block">
        <h3>Fan favourites · {windowLabel}</h3>
        <p className="chart-caption">Fans who think these players are delivering.</p>
        <div className="bar-chart">
          {(positive || []).length === 0 ? (
            <p className="status-line">No clear standouts in this window.</p>
          ) : (
            positive.map((r) => (
              <div className="bar-row" key={`p-${r.player_id}`}>
                <div className="bar-label">
                  <span className="bar-shirt pos">#{r.shirt}</span>
                  <span>{r.name}</span>
                </div>
                <div className="bar-track">
                  <span
                    className="bar-fill good"
                    style={{ width: `${Math.max(8, r.fan_approval_pct ?? r.fan_pct)}%` }}
                  />
                </div>
                <div className="bar-value">{r.fan_approval_pct ?? r.fan_pct}%</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function TeamHighlight({ side, highlight }) {
  if (!highlight) return null;
  if (side === "home") {
    const ch = highlight.chances || {};
    const del = highlight.deliveries || {};
    const chTotal = Math.max(1, (ch.used || 0) + Math.max(0, (ch.created || 0) - (ch.used || 0)));
    const usedPct = Math.round(((ch.used || 0) / chTotal) * 100);
    const delTotal = Math.max(1, (del.productive || 0) + (del.unproductive || 0));
    const prodPct = Math.round(((del.productive || 0) / delTotal) * 100);
    return (
      <div className="team-highlights">
        <div className="chart-block">
          <h3>Chances taken</h3>
          <div className="split-meter">
            <span className="split-used" style={{ width: `${usedPct}%` }} />
            <span className="split-rest" style={{ width: `${100 - usedPct}%` }} />
          </div>
          <div className="split-legend">
            <span>
              Used <strong>{ch.used ?? 0}</strong>
            </span>
            <span>
              Created <strong>{ch.created ?? 0}</strong>
            </span>
          </div>
          <p className="chart-caption">{ch.label}</p>
        </div>
        <div className="chart-block">
          <h3>Deliveries</h3>
          <div className="split-meter">
            <span className="split-used" style={{ width: `${prodPct}%` }} />
            <span className="split-rest" style={{ width: `${100 - prodPct}%` }} />
          </div>
          <div className="split-legend">
            <span>
              Productive <strong>{del.productive ?? 0}</strong>
            </span>
            <span>
              Poor <strong>{del.unproductive ?? 0}</strong>
            </span>
          </div>
          <p className="chart-caption">{del.label}</p>
        </div>
      </div>
    );
  }
  const pr = highlight.pressure || {};
  const cold = highlight.cold_start || {};
  return (
    <div className="team-highlights">
      <div className="chart-block">
        <h3>Defensive pressure</h3>
        <div className={`pressure-gauge side-${pr.vulnerable_side || "left"}`}>
          <div
            className="pressure-glow"
            style={{ opacity: 0.35 + (pr.intensity || 0.5) * 0.65 }}
          />
          <div className="pressure-label">{pr.label}</div>
        </div>
        <p className="chart-caption">{pr.summary}</p>
      </div>
      <div className="chart-block">
        <h3>{cold.headline || "Cold start"}</h3>
        <div className="cold-row">
          <div className="shirt tiny away">#{cold.shirt || "?"}</div>
          <div>
            <div className="stat-bad">
              Pass {Math.round((cold.passing_accuracy || 0) * 100)}%
            </div>
            <div className="status-line">{cold.loss_of_possession ?? 0} losses</div>
          </div>
        </div>
        <p className="chart-caption">{cold.verdict}</p>
      </div>
    </div>
  );
}

export default function FanTeamBoard({ board, onExplain, liveMinute, liveRunning }) {
  const slices = board?.slices || [];
  const liveIdx = useMemo(() => {
    if (liveMinute == null || Number.isNaN(liveMinute)) return -1;
    if (liveMinute >= 90) return Math.max(0, slices.length - 1);
    return Math.min(slices.length - 1, Math.max(0, Math.floor(liveMinute / 5)));
  }, [liveMinute, slices.length]);

  const [activeIdx, setActiveIdx] = useState(0);
  const [manualOverride, setManualOverride] = useState(false);

  useEffect(() => {
    setManualOverride(false);
  }, [board?.side]);

  useEffect(() => {
    if (!liveRunning || liveIdx < 0) return;
    if (!manualOverride) setActiveIdx(liveIdx);
  }, [liveRunning, liveIdx, manualOverride]);

  const safeIdx = Math.min(activeIdx, Math.max(0, slices.length - 1));
  const active = slices[safeIdx] || {
    label: "—",
    underperformers: [],
    standouts: [],
    crowd_calls: [],
  };

  const crowdCalls =
    liveRunning && (active.crowd_calls || []).length
      ? active.crowd_calls
      : board?.crowd_calls || [];

  if (!board) {
    return <p className="status-line">Load the match to unlock team insights.</p>;
  }

  return (
    <section className={`fan-team-board side-${board.side}`}>
      <header className="fan-team-head">
        <div className="fan-team-title-row">
          <h2>{board.team_name}</h2>
          {liveRunning && liveMinute != null && liveMinute < 90 ? (
            <span className="live-pill">LIVE {liveMinute.toFixed(1)}&apos;</span>
          ) : liveRunning && liveMinute != null && liveMinute >= 90 ? (
            <span className="live-pill muted">FT</span>
          ) : null}
        </div>
        <p className="sub">
          {board.side === "home" ? "Home" : "Away"} fan board · crowd + 5-minute pulse
        </p>
      </header>

      <CrowdCallHero
        calls={crowdCalls}
        side={board.side}
        liveLabel={liveRunning ? active.label : null}
        onExplain={onExplain}
      />

      <div className="slice-panel">
        <h3 className="slice-title">
          5-minute pulse
          {liveRunning ? " · follows the clock" : ""}
        </h3>
        <SliceScrubber
          slices={slices}
          activeIdx={safeIdx}
          liveIdx={liveIdx}
          onChange={(i) => {
            setManualOverride(true);
            setActiveIdx(i);
          }}
        />
        <p className="slice-progress">
          Window {safeIdx + 1} / {slices.length || 0}
          {liveRunning ? " · follows match clock" : ""}
        </p>
        <OpinionBars
          negative={active.underperformers}
          positive={active.standouts}
          windowLabel={active.label}
        />
      </div>

      <TeamHighlight side={board.side} highlight={board.highlight} />
    </section>
  );
}

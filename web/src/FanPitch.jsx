import { useEffect, useState } from "react";

export default function FanPitch({
  players = [],
  problems = [],
  onExplain,
  onAskAbout,
  liveMinute = null,
  liveRunning = false,
}) {
  const [selectedId, setSelectedId] = useState(null);
  const selected = players.find((p) => p.player_id === selectedId) || null;
  const problemCount = (problems || []).length;

  useEffect(() => {
    if (selectedId && !players.some((p) => p.player_id === selectedId)) {
      setSelectedId(null);
    }
  }, [players, selectedId]);

  const throughLabel =
    liveMinute != null && !Number.isNaN(liveMinute)
      ? `through ${Math.max(0, liveMinute).toFixed(1)}'`
      : "full match";

  return (
    <section
      className="column pitch-column"
      data-tour="tour-pitch"
      onClick={(e) => {
        if (e.target.closest(".pitch-player, .player-sheet")) return;
        onExplain?.("pitch", e.currentTarget);
      }}
    >
      <h2>Pitch</h2>
      <p className="sub">
        Click a player for live numbers ({throughLabel}). Pulse appears only when a
        problem is active
        {problemCount ? ` — ${problemCount} now` : ""}.
        {liveRunning ? " · LIVE" : ""}
      </p>
      <div className="pitch-board fan-pitch-board">
        <div className="pitch-markings">
          <div className="halfway" />
          <div className="center-circle" />
          <div className="box left-box" />
          <div className="box right-box" />
        </div>
        {players.map((p) => {
          const isSelected = selectedId === p.player_id;
          return (
            <button
              key={p.player_id}
              type="button"
              className={`pitch-player ${p.team_side} ${p.has_problem ? "problem" : ""} ${
                isSelected ? "selected" : ""
              }`}
              style={{ left: `${p.x_pct}%`, top: `${p.y_pct}%` }}
              title={`${p.name} · ${p.position}`}
              aria-pressed={isSelected}
              onClick={(e) => {
                e.stopPropagation();
                setSelectedId(p.player_id);
              }}
            >
              {p.has_problem && !isSelected ? (
                <span className="player-pulse" aria-hidden />
              ) : null}
              {isSelected ? <span className="player-selected-ring" aria-hidden /> : null}
              <span className="player-dot">#{p.shirt}</span>
            </button>
          );
        })}
        <div className="pitch-caption">
          {selected
            ? `Selected · ${selected.name} · ${selected.position}`
            : "Home → · Away ← · click a circle"}
        </div>
      </div>

      {selected ? (
        <div className="player-sheet" data-explain="playerSheet">
          <div className="player-sheet-head">
            <div className={`shirt tiny ${selected.team_side}`}>#{selected.shirt}</div>
            <div>
              <strong>
                {selected.name} · {selected.position}
              </strong>
              <div className="status-line">
                {selected.team_side === "home" ? "Northbridge" : "Riverdale"} · {throughLabel}
              </div>
            </div>
            {onAskAbout ? (
              <button type="button" className="ask-about" onClick={() => onAskAbout(selected)}>
                Ask about
              </button>
            ) : null}
            <button type="button" className="explain-close" onClick={() => setSelectedId(null)}>
              ×
            </button>
          </div>
          {selected.problem ? (
            <div className="problem-chip">{selected.problem.label}</div>
          ) : (
            <div className="status-line">No flagged problem on this player right now.</div>
          )}
          <div className="player-stat-grid">
            <div>
              <span>Pass %</span>
              <strong>
                {selected.stats?.pass_accuracy_pct != null
                  ? `${selected.stats.pass_accuracy_pct}%`
                  : selected.stats?.passes
                    ? "0%"
                    : "n/a"}
              </strong>
            </div>
            <div>
              <span>Passes</span>
              <strong>{selected.stats?.passes ?? 0}</strong>
            </div>
            <div>
              <span>Touches</span>
              <strong>{selected.stats?.touches ?? 0}</strong>
            </div>
            {selected.position === "GK" ? (
              <>
                <div>
                  <span>Saves</span>
                  <strong>{selected.stats?.saves ?? 0}</strong>
                </div>
                <div>
                  <span>Goals conc.</span>
                  <strong>{selected.stats?.goals_conceded ?? 0}</strong>
                </div>
                <div>
                  <span>Losses</span>
                  <strong>{selected.stats?.losses ?? 0}</strong>
                </div>
              </>
            ) : (
              <>
                <div>
                  <span>Losses</span>
                  <strong>{selected.stats?.losses ?? 0}</strong>
                </div>
                <div>
                  <span>Duels W/L</span>
                  <strong>
                    {selected.stats?.duels_won ?? 0}/{selected.stats?.duels_lost ?? 0}
                  </strong>
                </div>
                <div>
                  <span>Shots on/tot</span>
                  <strong>
                    {selected.stats?.shots_on ?? 0}/{selected.stats?.shots ?? 0}
                  </strong>
                </div>
                <div>
                  <span>Crosses</span>
                  <strong>{selected.stats?.crosses ?? 0}</strong>
                </div>
                {selected.position === "ST" || (selected.stats?.goals ?? 0) > 0 ? (
                  <div>
                    <span>Goals</span>
                    <strong>{selected.stats?.goals ?? 0}</strong>
                  </div>
                ) : null}
              </>
            )}
          </div>
        </div>
      ) : (
        <p className="status-line" style={{ marginTop: "0.65rem" }}>
          Select a circled player to open their live snapshot.
        </p>
      )}
    </section>
  );
}

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import AgentTrace from "./AgentTrace.jsx";
import FanChat from "./FanChat.jsx";
import FanPitch from "./FanPitch.jsx";
import FanTeamBoard from "./FanTeamBoard.jsx";
import { AboutModal, ExplainPopover, TourBubble, useTargetRect } from "./GuideOverlays.jsx";
import { EXPLAIN, STORAGE_ABOUT, STORAGE_TOUR, TOUR_STEPS } from "./guideContent.js";

function CoachPitch({ selectedAlert, alerts, onExplain }) {
  const coachZone = (() => {
    const id = selectedAlert || alerts?.[0]?.alert_id || "";
    if (id === "chaos_press_mid" || id === "midfield_link_break") return "mid";
    if (id === "wasteful_finishing" || id === "shot_speed_spike" || id === "low_defensive_contacts")
      return "box";
    if (id === "unproductive_crosses" || id.includes("flank") || id.includes("cross")) return "right";
    return "right";
  })();

  return (
    <section
      className="column pitch-column"
      data-tour="tour-pitch"
      onClick={(e) => onExplain("pitch", e.currentTarget)}
    >
      <h2>Pitch</h2>
      <p className="sub">Live tactical zones from active coaching alerts.</p>
      <div className="pitch-board">
        <div className="pitch-markings">
          <div className="halfway" />
          <div className="center-circle" />
          <div className="box left-box" />
          <div className="box right-box" />
        </div>
        <div className={`pitch-hot coach-${coachZone}`} />
        <div className="pitch-caption">
          {selectedAlert
            ? selectedAlert.replaceAll("_", " ")
            : alerts?.length
              ? "Tracking active leaks"
              : "Waiting for live alerts"}
        </div>
      </div>
    </section>
  );
}

export default function App() {
  const [view, setView] = useState("fan");
  const [status, setStatus] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [shortlist, setShortlist] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [halftime, setHalftime] = useState(null);
  const [fanLive, setFanLive] = useState(null);
  const [chat, setChat] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [fanAsk, setFanAsk] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const esRef = useRef(null);

  const [aboutOpen, setAboutOpen] = useState(false);
  const [tourIndex, setTourIndex] = useState(-1);
  const [explain, setExplain] = useState(null);
  const [explainRect, setExplainRect] = useState(null);

  const touring = tourIndex >= 0;
  const tourStep = touring ? TOUR_STEPS[tourIndex] : null;
  const tourRect = useTargetRect(tourStep?.target, touring && Boolean(tourStep?.target));

  useEffect(() => {
    try {
      if (!localStorage.getItem(STORAGE_ABOUT)) setAboutOpen(true);
    } catch {
      setAboutOpen(true);
    }
  }, []);

  const syncViewer = useCallback(async (nextView = view) => {
    await api.setViewer({ mode: nextView, language: "en" });
    setView(nextView);
  }, [view]);

  const loadHalftime = useCallback(async () => {
    const ht = await api.halftime();
    setHalftime(ht);
  }, []);

  const refreshStatus = useCallback(async () => {
    const st = await api.status();
    setStatus(st);
    return st;
  }, []);

  const openStream = useCallback(
    async (speed = 140) => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      const es = new EventSource(api.streamUrl(speed));
      esRef.current = es;
      es.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "connected" || msg.type === "done" || msg.type === "state") {
            setStatus((prev) => ({ ...(prev || {}), ...(msg.payload || {}) }));
          }
          if (msg.type === "alert") {
            const payload = msg.payload || {};
            setAlerts((prev) => {
              if (prev.some((a) => a.alert_id === payload.alert_id && a.t_ms === payload.t_ms)) {
                return prev;
              }
              return [payload, ...prev].slice(0, 10);
            });
            setSelectedAlert(payload.alert_id);
          }
        } catch {
          /* ignore */
        }
      };
      es.onerror = () => {
        es.close();
        esRef.current = null;
        refreshStatus().catch(() => {});
      };
    },
    [refreshStatus],
  );

  useEffect(() => () => esRef.current?.close(), []);

  useEffect(() => {
    if (!selectedAlert || view !== "coach") return;
    api.shortlist(selectedAlert).then(setShortlist).catch(() => setShortlist(null));
  }, [selectedAlert, view]);

  const liveBucket = Math.floor((status?.match_minute ?? 0) * 2) / 2;

  useEffect(() => {
    if (view !== "fan" || !status?.loaded) return undefined;
    let cancelled = false;
    const m = status?.match_minute ?? 0;
    api
      .fanLive(m)
      .then((data) => {
        if (!cancelled) setFanLive(data);
      })
      .catch(() => {
        if (!cancelled) setFanLive(null);
      });
    return () => {
      cancelled = true;
    };
  }, [view, status?.loaded, liveBucket, status?.match_minute]);

  const bootstrap = useCallback(async () => {
    setBusy(true);
    setError("");
    setAlerts([]);
    try {
      await api.load("syn-001");
      await syncViewer(view);
      await loadHalftime();
      await api.start(140);
      await openStream(140);
      await refreshStatus();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }, [view, syncViewer, loadHalftime, openStream, refreshStatus]);

  async function togglePlayback() {
    if (status?.running) {
      await api.pause();
      esRef.current?.close();
      esRef.current = null;
      await refreshStatus();
      return;
    }
    if (!status?.loaded) {
      setError("Load & run the match first.");
      return;
    }
    setError("");
    try {
      await api.start(140);
      await openStream(140);
      await refreshStatus();
    } catch (e) {
      setError(String(e.message || e));
    }
  }

  const switchView = useCallback(
    async (next) => {
      await syncViewer(next);
      if (next === "fan") await loadHalftime();
    },
    [syncViewer, loadHalftime],
  );

  async function sendChat(e) {
    e.preventDefault();
    const message = chatInput.trim();
    if (!message) return;
    setChatInput("");
    setChat((prev) => [...prev, { role: "user", text: message }]);
    try {
      const res = await api.chat(message);
      setChat((prev) => [
        ...prev,
        {
          role: "agent",
          text: res.reply,
          trace: res.trace,
          engine: res.engine,
          recovered: res.recovered,
        },
      ]);
      const shortCall = (res.tool_calls || []).find((t) => t.tool === "propose_roles_for_alert");
      if (shortCall?.result) setShortlist(shortCall.result);
    } catch (err) {
      setChat((prev) => [...prev, { role: "agent", text: String(err.message || err) }]);
    }
  }

  function closeAbout() {
    setAboutOpen(false);
    try {
      localStorage.setItem(STORAGE_ABOUT, "1");
    } catch {
      /* ignore */
    }
  }

  function startTour() {
    setAboutOpen(false);
    setExplain(null);
    try {
      localStorage.setItem(STORAGE_ABOUT, "1");
    } catch {
      /* ignore */
    }
    setTourIndex(0);
  }

  function endTour() {
    setTourIndex(-1);
    try {
      localStorage.setItem(STORAGE_TOUR, "1");
    } catch {
      /* ignore */
    }
  }

  async function tourNext() {
    const step = TOUR_STEPS[tourIndex];
    if (step?.autoAction === "bootstrap" && !status?.loaded) {
      await bootstrap();
    }
    if (step?.autoAction === "switchCoach") {
      await switchView("coach");
    }
    if (step?.view === "fan" && view !== "fan" && step.autoAction !== "switchCoach") {
      await switchView("fan");
    }
    if (tourIndex >= TOUR_STEPS.length - 1) {
      endTour();
      return;
    }
    const next = TOUR_STEPS[tourIndex + 1];
    if (next?.view === "fan") await switchView("fan");
    if (next?.view === "coach") await switchView("coach");
    setTourIndex((i) => i + 1);
  }

  async function tourBack() {
    if (tourIndex <= 0) return;
    const prev = TOUR_STEPS[tourIndex - 1];
    if (prev?.view === "fan") await switchView("fan");
    if (prev?.view === "coach") await switchView("coach");
    setTourIndex((i) => i - 1);
  }

  function openExplain(key, el) {
    if (touring) return;
    const item = EXPLAIN[key];
    if (!item) return;
    const r = el?.getBoundingClientRect?.();
    setExplain(item);
    setExplainRect(
      r ? { top: r.top, left: r.left, bottom: r.bottom, width: r.width, height: r.height } : null,
    );
  }

  const loc = halftime?.localized;
  const teamBoards = loc?.team_boards || halftime?.team_boards;
  const pitchPlayers = fanLive?.pitch_players || loc?.pitch_players || [];
  const problems = fanLive?.problems || loc?.problems || [];
  const scoreline = halftime?.scoreline || "1-1";
  const home = halftime?.home_team || "Northbridge FC";
  const away = halftime?.away_team || "Riverdale United";
  const minute = status?.match_minute;
  const fanMode = view === "fan";

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="brand">
          Pitch<span>Pulse</span>
        </h1>
        <div className="scoreboard">
          <div className="phase">
            {fanMode ? "Match Day Summary" : "Pro Bench — Live"}
          </div>
          <div className="score">
            {home} {scoreline} {away}
          </div>
          <div className="clock">
            {fanMode
              ? status?.running || status?.loaded
                ? `${(minute ?? 0).toFixed(1)}' · ${status?.running ? "live" : "paused"}`
                : "90:00"
              : `${(minute ?? 0).toFixed(1)}' · ${
                  status?.running ? "live" : status?.loaded ? "paused" : "idle"
                }`}
          </div>
        </div>
        <div className="top-actions">
          <button type="button" onClick={() => setAboutOpen(true)}>
            About
          </button>
          <button type="button" onClick={startTour}>
            Tour
          </button>
          <button
            type="button"
            className="primary"
            data-tour="tour-load"
            disabled={busy}
            onClick={() => bootstrap()}
            onDoubleClick={(e) => openExplain("load", e.currentTarget)}
            title="Double-click for a short explanation"
          >
            Load & run syn-001
          </button>
          <button
            type="button"
            disabled={busy || (!status?.loaded && !status?.running)}
            onClick={togglePlayback}
          >
            {status?.running ? "Pause" : "Play"}
          </button>
          <span
            className="tab-group"
            data-tour="tour-tabs"
            onDoubleClick={(e) => openExplain("tabs", e.currentTarget)}
            title="Double-click for a short explanation"
          >
            <button
              type="button"
              className={fanMode ? "active" : ""}
              onClick={() => switchView("fan")}
            >
              Fan
            </button>
            <button
              type="button"
              className={!fanMode ? "active" : ""}
              onClick={() => switchView("coach")}
            >
              Coach
            </button>
          </span>
        </div>
      </header>

      {error ? <p style={{ color: "var(--danger)" }}>{error}</p> : null}

      {fanMode ? (
        <div className="fan-layout">
          <div
            className="fan-teams"
            data-tour="tour-fan-insights"
            onClick={(e) => {
              if (e.target.closest("[data-explain], button")) return;
              openExplain("fanInsights", e.currentTarget);
            }}
          >
            <FanTeamBoard
              board={teamBoards?.home}
              onExplain={openExplain}
              liveMinute={minute}
              liveRunning={Boolean(status?.running)}
            />
            <FanTeamBoard
              board={teamBoards?.away}
              onExplain={openExplain}
              liveMinute={minute}
              liveRunning={Boolean(status?.running)}
            />
          </div>
          <div className="fan-live-row">
            <FanPitch
              players={pitchPlayers}
              problems={problems}
              onExplain={openExplain}
              onAskAbout={(p) =>
                setFanAsk({
                  text: `How is #${p.shirt} ${p.name} doing, and what do the fans think?`,
                  nonce: Date.now(),
                })
              }
              liveMinute={minute ?? fanLive?.minute ?? 0}
              liveRunning={Boolean(status?.running)}
            />
            <FanChat ask={fanAsk} onExplain={openExplain} />
          </div>
        </div>
      ) : (
        <div className="split">
          <section
            className="column"
            data-tour="tour-coach"
            onClick={(e) => {
              if (e.target.closest("[data-explain], form, input, button, .alert")) return;
              openExplain("coachAnalytics", e.currentTarget);
            }}
          >
            <h2>Coach Analytics</h2>
            <p className="sub">Live leaks, evidence, and who can fix them.</p>
            <div className="coach-body">
              <div
                className="alert-rail"
                data-tour="tour-alerts"
                data-explain="alerts"
                onClick={(e) => {
                  if (e.target.closest(".alert")) return;
                  e.stopPropagation();
                  openExplain("alerts", e.currentTarget);
                }}
              >
                {alerts.length === 0 ? (
                  <p className="status-line">
                    Start playback to surface live flank / midfield leaks as the clock advances.
                  </p>
                ) : (
                  alerts.map((a) => (
                    <article
                      key={`${a.alert_id}-${a.t_ms}`}
                      className={`alert ${a.severity || "warning"}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedAlert(a.alert_id);
                        openExplain("alerts", e.currentTarget);
                      }}
                    >
                      <div className="id">{a.alert_id}</div>
                      <div className="meta">
                        {a.match_minute?.toFixed?.(1) ?? "—"}&apos; · {a.severity}
                      </div>
                      <p>{a.personalized?.text || "Alert fired"}</p>
                    </article>
                  ))
                )}
              </div>

              <div
                data-tour="tour-shortlist"
                data-explain="shortlist"
                onClick={(e) => {
                  e.stopPropagation();
                  openExplain("shortlist", e.currentTarget);
                }}
              >
                <strong style={{ fontFamily: "var(--font-display)", letterSpacing: "0.04em" }}>
                  WHO CAN FIX THIS
                </strong>
                {!shortlist ? (
                  <p className="status-line">Select a live alert to score bench profiles.</p>
                ) : (
                  <>
                    <p className="status-line">{shortlist.gap}</p>
                    {(shortlist.candidates || []).map((c) => (
                      <div className="candidate" key={c.player_id}>
                        <div>
                          {c.name} · {c.position} · fit {c.fit_score}
                        </div>
                        <div className="why">{c.why}</div>
                      </div>
                    ))}
                  </>
                )}
              </div>

              <div
                data-tour="tour-agent"
                data-explain="agent"
                onClick={(e) => {
                  if (e.target.closest("form, input, button")) return;
                  e.stopPropagation();
                  openExplain("agent", e.currentTarget);
                }}
              >
                <strong style={{ fontFamily: "var(--font-display)", letterSpacing: "0.04em" }}>
                  BENCH AGENT
                </strong>
                <div className="chat-log" style={{ marginTop: "0.4rem" }}>
                  {chat.length === 0 ? (
                    <div className="bubble">Ask: “What is leaking?” / “Who can fix the flank?”</div>
                  ) : (
                    chat.map((m, i) => (
                      <div key={i} className={`bubble ${m.role}`}>
                        {m.text}
                        <AgentTrace trace={m.trace} engine={m.engine} recovered={m.recovered} />
                      </div>
                    ))
                  )}
                </div>
                <form className="chat-form" onSubmit={sendChat}>
                  <input
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Coach agent…"
                  />
                  <button className="primary" type="submit">
                    Send
                  </button>
                </form>
              </div>
            </div>
          </section>
          <CoachPitch
            selectedAlert={selectedAlert}
            alerts={alerts}
            onExplain={openExplain}
          />
        </div>
      )}

      <AboutModal
        open={aboutOpen && !touring}
        onClose={closeAbout}
        onStartTour={startTour}
      />
      <TourBubble
        step={tourStep}
        stepIndex={Math.max(0, tourIndex)}
        total={TOUR_STEPS.length}
        rect={tourRect}
        onNext={tourNext}
        onBack={tourBack}
        onSkip={endTour}
      />
      <ExplainPopover
        item={explain}
        anchorRect={explainRect}
        onClose={() => setExplain(null)}
      />
    </div>
  );
}

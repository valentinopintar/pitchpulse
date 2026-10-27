export const ABOUT = {
  title: "What is PitchPulse?",
  body: [
    "PitchPulse turns synthetic match events into explainable match intelligence for two audiences.",
    "Fan tab = living-room Match Day Summary at halftime (simple storylines, no coaching jargon).",
    "Coach tab = live bench feed (leaks, who can fix them, agent). Same engine — separate product views.",
    "This demo uses one synthetic match (syn-001). Fan / Coach tabs simulate two experiences for judges.",
  ],
  bullets: [
    "Load & run syn-001 to start the replay and unlock the fan summary",
    "Explore Fan Insights + pitch, then switch to Coach for live alerts",
    "Click any component for a short “what is this?” explanation",
  ],
};

export const EXPLAIN = {
  load: {
    title: "Load & run",
    text: "Starts the synthetic match replay, loads halftime fan cards, and opens the live event stream used by Coach alerts.",
  },
  fanInsights: {
    title: "Fan Insights",
    text: "Home left / Away right: crowd calls (the product heart), 5-minute underperformer pulse, then team highlights. Full-width pitch below.",
  },
  playerSheet: {
    title: "Player snapshot",
    text: "Click any circle on the pitch for that player's first-half numbers. Pulsing circles are problem positions only.",
  },
  coldStart: {
    title: "Did they start poorly?",
    text: "Fan card built from first-half events: pass accuracy and losses for a player who looked shaky early.",
  },
  flankCard: {
    title: "Defensive pressure",
    text: "Shows where first-half pressure stacked (e.g. vulnerable flank) using crosses and zone events — not a coach playbook.",
  },
  chanceCard: {
    title: "Chances taken?",
    text: "How many big chances the focal attacker got in the first half, and how many they actually used (conversion).",
  },
  deliveryCard: {
    title: "Deliveries productive?",
    text: "Crosses and cutbacks: volume vs productive balls into the box — not every whip-in counts.",
  },
  crowdCard: {
    title: "Crowd call",
    text: "Main beat of PitchPulse: mixed positive and negative fan opinions with % support (boost vs pressure). During Load & run it follows the match clock every 5 minutes.",
  },
  pitch: {
    title: "Pitch",
    text: "Fan mode: full squad circles — click for stats; pulse = problem position. Coach mode: tactical zone heat from live alerts.",
  },
  coachAnalytics: {
    title: "Coach Analytics",
    text: "Live bench workspace: tactical alerts as the clock advances, bench shortlist for the gap, and a coach agent.",
  },
  alerts: {
    title: "Live alerts",
    text: "Rule-based coaching cues from rolling match state (flank overload, midfield chaos, etc.). Click an alert to score who on the bench can fix it.",
  },
  shortlist: {
    title: "Who can fix this",
    text: "Bench profiles scored against the alert gap (e.g. cross-defending full-back) from the synthetic roster catalog.",
  },
  fanChat: {
    title: "Fan Companion",
    text: "A fan-side agent team (Crowd Pulse + Storyteller) answers what the stands think and how a player is doing — summary level, no coaching detail. Tools are called over MCP; answers come back in your language when an LLM is configured.",
  },
  agent: {
    title: "Bench agent team",
    text: "An Orchestrator hands your question to a Match Analyst, Bench Scout and Storyteller that share one blackboard and call the same tools as the UI. Open the trace under each answer to see every handoff.",
  },
  tabs: {
    title: "Fan / Coach tabs",
    text: "Demo simulation of two products. Fans would only see the Fan experience; coaches only the bench. Here you can switch to evaluate both.",
  },
};

export const TOUR_STEPS = [
  {
    id: "load",
    target: "tour-load",
    title: "1 · Start the demo match",
    text: "Click Load & run syn-001 (or press Next and we will start it). This generates the live stream and fan halftime summary.",
    view: "fan",
    autoAction: "bootstrap",
  },
  {
    id: "fan",
    target: "tour-fan-insights",
    title: "2 · Fan Insights",
    text: "Home left / Away right: crowd calls + 5-minute fan pulse. Full-width pitch below.",
    view: "fan",
  },
  {
    id: "pitch-fan",
    target: "tour-pitch",
    title: "3 · Pitch (Fan)",
    text: "Click player circles for HT stats. Only problem positions pulse — not every alert.",
    view: "fan",
  },
  {
    id: "switch-coach",
    target: "tour-tabs",
    title: "4 · Switch to Coach",
    text: "Open the Coach tab to see the live bench experience. In a real product, this would be a separate app for staff.",
    view: "coach",
    autoAction: "switchCoach",
  },
  {
    id: "alerts",
    target: "tour-alerts",
    title: "5 · Live coaching alerts",
    text: "As the clock advances, PitchPulse fires explainable leaks. Click an alert when one appears to feed the shortlist.",
    view: "coach",
  },
  {
    id: "shortlist",
    target: "tour-shortlist",
    title: "6 · Who can fix this",
    text: "Bench candidates scored for the selected gap — immediate tactical options for the staff.",
    view: "coach",
    // Sit beside the card (toward pitch) so shortlist text stays readable.
    placement: "right",
  },
  {
    id: "agent",
    target: "tour-agent",
    title: "7 · Bench agent",
    text: "Ask the agent about leaks, shortlists, or the halftime summary. Same intelligence engine, conversational surface.",
    view: "coach",
    placement: "right",
  },
  {
    id: "done",
    target: null,
    title: "Tour complete",
    text: "You have seen both views. Re-open About or Tour anytime from the header. Click any panel for a short explanation.",
    view: null,
  },
];

export const STORAGE_ABOUT = "pitchpulse_about_seen";
export const STORAGE_TOUR = "pitchpulse_tour_seen";

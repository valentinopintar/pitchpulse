const API_BASE = import.meta.env.VITE_API_URL || "/api";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

export const api = {
  health: () => request("/health"),
  load: (matchId = "syn-001") =>
    request("/replay/load", { method: "POST", body: JSON.stringify({ match_id: matchId }) }),
  start: (speed = 120) =>
    request("/replay/start", { method: "POST", body: JSON.stringify({ speed }) }),
  pause: () => request("/replay/pause", { method: "POST", body: "{}" }),
  status: () => request("/replay/status"),
  setViewer: (viewer) =>
    request("/viewer", { method: "POST", body: JSON.stringify(viewer) }),
  shortlist: (alertId) => request(`/shortlist/${alertId}`),
  chat: (message, audience = "coach") =>
    request("/agent/chat", { method: "POST", body: JSON.stringify({ message, audience }) }),
  substitution: (momentId) => request(`/substitutions/${momentId}`),
  halftime: () => request("/fan/halftime"),
  fanLive: (minute = 0) => request(`/fan/live?minute=${encodeURIComponent(minute)}`),
  streamUrl: (speed = 120) => `${API_BASE}/replay/stream?speed=${speed}&autostart=true`,
};

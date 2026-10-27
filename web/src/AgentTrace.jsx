import { useState } from "react";

const AGENT_LABEL = {
  orchestrator: "Orchestrator",
  analyst: "Match Analyst",
  tactician: "Tactician",
  bench_scout: "Bench Scout",
  storyteller: "Storyteller",
  crowd_pulse: "Crowd Pulse",
};

const ENGINE_LABEL = {
  azure_openai: "Azure OpenAI",
  openai: "OpenAI",
  rules: "Rules",
  mixed: "LLM + recovery",
};

function stepText(t) {
  if (t.kind === "tool") {
    const args = Object.entries(t.args || {})
      .map(([k, v]) => `${k}=${v}`)
      .join(", ");
    return `${t.ok ? "" : "✗ "}${t.detail}(${args})`;
  }
  if (t.kind === "report") return `report (${t.source})`;
  return t.detail;
}

export default function AgentTrace({ trace, engine, recovered }) {
  const [open, setOpen] = useState(false);
  if (!trace?.length) return null;
  const handoffs = trace.filter((t) => t.kind === "handoff").length;
  const tools = trace.filter((t) => t.kind === "tool").length;
  const totalMs = trace[trace.length - 1].ms;

  return (
    <div className="agent-trace">
      <button type="button" className="trace-toggle" onClick={() => setOpen((v) => !v)}>
        <span className={`engine-badge ${engine}`}>{ENGINE_LABEL[engine] || engine}</span>
        {handoffs} handoffs · {tools} tools · {totalMs} ms{recovered ? " · recovered" : ""}
        <span className="trace-caret">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <ol className="trace-steps">
          {trace.map((t) => (
            <li key={t.step} className={`trace-step ${t.kind}`}>
              <span className={`agent-chip ${t.agent}`}>{AGENT_LABEL[t.agent] || t.agent}</span>
              <span className="trace-kind">{t.kind}</span>
              <span className="trace-detail" title={t.kind === "report" ? t.detail : undefined}>
                {stepText(t)}
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

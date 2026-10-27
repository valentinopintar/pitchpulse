import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import AgentTrace from "./AgentTrace.jsx";

const SUGGESTIONS = [
  "What do the other fans think right now?",
  "Who are the fans unhappy with — and do the numbers back them up?",
  "Who is the man of the match so far?",
  "Tell me the story of the match",
];

export default function FanChat({ ask, onExplain }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const logRef = useRef(null);

  async function send(text) {
    const message = text.trim();
    if (!message || pending) return;
    setInput("");
    setPending(true);
    setMessages((prev) => [...prev, { role: "user", text: message }]);
    try {
      const res = await api.chat(message, "fan");
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          text: res.reply,
          trace: res.trace,
          engine: res.engine,
          recovered: res.recovered,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "agent", text: String(err.message || err) }]);
    } finally {
      setPending(false);
    }
  }

  // Questions pushed from the pitch ("Ask about this player").
  useEffect(() => {
    if (ask?.text) send(ask.text);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ask?.nonce]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [messages, pending]);

  return (
    <section
      className="column fan-chat"
      data-tour="tour-fan-chat"
      onClick={(e) => {
        if (e.target.closest("form, input, button, .bubble")) return;
        onExplain?.("fanChat", e.currentTarget);
      }}
    >
      <h2>Fan Companion</h2>
      <p className="sub">Ask what the stands think or how a player is doing — summary level.</p>
      <div className="chat-log fan-chat-log" ref={logRef}>
        {messages.length === 0 ? (
          <div className="fan-chat-empty">
            {SUGGESTIONS.map((s) => (
              <button key={s} type="button" className="suggestion" onClick={() => send(s)}>
                {s}
              </button>
            ))}
            <div className="status-line">Tip: click a player on the pitch, then “Ask about”.</div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`bubble ${m.role}`}>
              {m.text}
              <AgentTrace trace={m.trace} engine={m.engine} recovered={m.recovered} />
            </div>
          ))
        )}
        {pending ? <div className="bubble agent typing">Asking the stands…</div> : null}
      </div>
      <form
        className="chat-form"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask in any language…"
          disabled={pending}
        />
        <button className="primary" type="submit" disabled={pending}>
          Send
        </button>
      </form>
    </section>
  );
}

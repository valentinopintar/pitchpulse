import { useEffect, useState } from "react";

export function AboutModal({ open, onClose, onStartTour }) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <h2>What is PitchPulse?</h2>
        <p>
          PitchPulse turns synthetic match events into explainable match intelligence for two
          audiences.
        </p>
        <ul>
          <li>
            <strong>Fan</strong> — living-room Match Day Summary at halftime (simple storylines).
          </li>
          <li>
            <strong>Coach</strong> — live bench feed (leaks, bench fix, agent).
          </li>
          <li>Same engine. Fan / Coach tabs simulate two products for this hackathon demo.</li>
        </ul>
        <p className="modal-hint">
          Tip: click any panel later for a short “what is this?” popup. Or take the guided tour.
        </p>
        <div className="modal-actions">
          <button type="button" onClick={onClose}>
            Got it
          </button>
          <button type="button" className="primary" onClick={onStartTour}>
            Take a quick tour
          </button>
        </div>
      </div>
    </div>
  );
}

function measureEl(selector) {
  const el = document.querySelector(selector);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return { top: r.top, left: r.left, width: r.width, height: r.height, bottom: r.bottom, right: r.right };
}

function tourBubbleStyle(rect, placement, pitchRect) {
  if (!rect) {
    return { top: "30%", left: "50%", transform: "translateX(-50%)" };
  }
  const bubbleW = 340;
  const maxLeft = window.innerWidth - bubbleW - 12;
  const maxTop = window.innerHeight - 240;

  // Park on the pitch column, vertically aligned with the spotlighted card.
  if (placement === "right") {
    const top = Math.min(maxTop, Math.max(12, rect.top));
    if (pitchRect && pitchRect.width > 80) {
      return {
        top,
        left: Math.min(maxLeft, Math.max(12, pitchRect.left + 16)),
      };
    }
    return {
      top,
      left: Math.min(maxLeft, Math.max(window.innerWidth * 0.52, 12)),
    };
  }

  return {
    top: Math.min(maxTop, rect.bottom + 12),
    left: Math.min(maxLeft, Math.max(12, rect.left)),
  };
}

export function TourBubble({ step, stepIndex, total, rect, onNext, onBack, onSkip }) {
  if (!step) return null;
  const pitchRect = step.placement === "right" ? measureEl('[data-tour="tour-pitch"]') : null;
  const style = tourBubbleStyle(rect, step.placement, pitchRect);

  return (
    <>
      {rect ? (
        <div
          className="tour-spotlight"
          style={{
            top: rect.top - 6,
            left: rect.left - 6,
            width: rect.width + 12,
            height: rect.height + 12,
          }}
        />
      ) : (
        <div className="tour-dim" />
      )}
      <div className="tour-bubble" style={style}>
        <div className="tour-step">
          Step {stepIndex + 1} / {total}
        </div>
        <h3>{step.title}</h3>
        <p>{step.text}</p>
        <div className="modal-actions">
          <button type="button" onClick={onSkip}>
            Skip
          </button>
          <button type="button" disabled={stepIndex === 0} onClick={onBack}>
            Back
          </button>
          <button type="button" className="primary" onClick={onNext}>
            {stepIndex >= total - 1 ? "Finish" : "Next"}
          </button>
        </div>
      </div>
    </>
  );
}

export function ExplainPopover({ item, anchorRect, onClose }) {
  if (!item) return null;
  const style = anchorRect
    ? {
        top: Math.min(window.innerHeight - 180, anchorRect.bottom + 8),
        left: Math.min(window.innerWidth - 340, Math.max(12, anchorRect.left)),
      }
    : { top: "40%", left: "50%", transform: "translateX(-50%)" };

  return (
    <div className="explain-pop" style={style} role="dialog">
      <div className="explain-head">
        <strong>{item.title}</strong>
        <button type="button" className="explain-close" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>
      <p>{item.text}</p>
    </div>
  );
}

export function useTargetRect(targetId, active) {
  const [rect, setRect] = useState(null);
  useEffect(() => {
    if (!active || !targetId) {
      setRect(null);
      return undefined;
    }
    const measure = () => {
      const el = document.querySelector(`[data-tour="${targetId}"]`);
      if (!el) {
        setRect(null);
        return;
      }
      const r = el.getBoundingClientRect();
      setRect({ top: r.top, left: r.left, width: r.width, height: r.height, bottom: r.bottom });
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    };
    measure();
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    const t = window.setInterval(measure, 400);
    return () => {
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
      window.clearInterval(t);
    };
  }, [targetId, active]);
  return rect;
}

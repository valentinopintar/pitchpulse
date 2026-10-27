"""FastAPI studio API — replay control + SSE + explain / personalize."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse

from pitchpulse.agent.chat import agent_chat
from pitchpulse.agent import tools as agent_tools
from pitchpulse.agent.team import SPECIALISTS
from pitchpulse.api.replay_session import SESSION, ReplayStatus
from pitchpulse.api.studio_state import STUDIO
from pitchpulse.config import load_dotenv
from pitchpulse.data.paths import match_dir
from pitchpulse.explain.azure_client import azure_configured
from pitchpulse.explain.service import EXPLAIN
from pitchpulse.mcp import server as mcp_server
from pitchpulse.personalize.halftime import build_fan_live, build_halftime_summary
from pitchpulse.personalize.viewer import ViewerProfile
from pitchpulse.render.overlay import build_overlay_packet
from pitchpulse.shortlist.service import propose_roles_for_alert


def _status_dict(st: ReplayStatus) -> dict[str, Any]:
    return {
        "match_id": st.match_id,
        "loaded": st.loaded,
        "running": st.running,
        "speed": st.speed,
        "index": st.index,
        "total_events": st.total_events,
        "t_ms": st.t_ms,
        "match_minute": st.match_minute,
        "active_alert_ids": st.active_alert_ids,
        "viewer": STUDIO.viewer.to_dict(),
        "azure_configured": azure_configured(),
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_dotenv()
    yield


api_app = FastAPI(title="PitchPulse AI", version="0.1.0", lifespan=lifespan)
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api_app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "pitchpulse-ai",
        "azure_configured": azure_configured(),
    }


@api_app.get("/replay/status")
def replay_status() -> dict[str, Any]:
    return _status_dict(SESSION.status())


@api_app.post("/replay/load")
def replay_load(body: dict[str, Any]) -> dict[str, Any]:
    match_id = body.get("match_id", "syn-001")
    if not (match_dir(match_id) / "events.jsonl").exists():
        raise HTTPException(status_code=404, detail=f"Match not found: {match_id}")
    try:
        st = SESSION.load(match_id)
        STUDIO.bind_match(match_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _status_dict(st)


@api_app.post("/replay/start")
def replay_start(body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    speed = float(body.get("speed", 0.0))
    try:
        st = SESSION.start(speed=speed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _status_dict(st)


@api_app.post("/replay/pause")
def replay_pause() -> dict[str, Any]:
    return _status_dict(SESSION.pause())


@api_app.post("/replay/speed")
def replay_speed(body: dict[str, Any]) -> dict[str, Any]:
    speed = float(body.get("speed", 0.0))
    return _status_dict(SESSION.set_speed(speed))


@api_app.post("/replay/seek")
def replay_seek(body: dict[str, Any]) -> dict[str, Any]:
    if "t_ms" not in body:
        raise HTTPException(status_code=400, detail="t_ms required")
    try:
        st = SESSION.seek(int(body["t_ms"]))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _status_dict(st)


@api_app.get("/viewer")
def get_viewer() -> dict[str, Any]:
    return STUDIO.viewer.to_dict()


@api_app.post("/viewer")
def set_viewer(body: dict[str, Any]) -> dict[str, Any]:
    STUDIO.viewer = ViewerProfile.from_dict(body)
    return STUDIO.viewer.to_dict()


@api_app.post("/explain/alert")
def explain_alert(body: dict[str, Any]) -> dict[str, Any]:
    alert_id = body.get("alert_id")
    if not alert_id:
        raise HTTPException(status_code=400, detail="alert_id required")
    evidence = body.get("evidence") or {}
    match_minute = body.get("match_minute")
    use_llm = bool(body.get("use_llm", True))
    related = body.get("related_player_ids") or STUDIO.related_players(alert_id)
    explanation = EXPLAIN.explain_alert(
        alert_id=alert_id,
        evidence=evidence,
        match_minute=match_minute,
        related_player_ids=related,
        use_llm=use_llm,
    )
    personalized = EXPLAIN.for_viewer(explanation, STUDIO.viewer)
    overlay = build_overlay_packet(
        alert_id=alert_id,
        t_ms=int(body.get("t_ms") or 0),
        explanation=explanation,
        severity=str(body.get("severity") or "warning"),
    )
    return {
        "explanation": explanation,
        "personalized": personalized,
        "overlay": overlay,
        "viewer": STUDIO.viewer.to_dict(),
    }


@api_app.get("/substitutions")
def list_substitutions() -> dict[str, Any]:
    if not STUDIO.match_id:
        raise HTTPException(status_code=400, detail="Load a match first")
    return {"match_id": STUDIO.match_id, "moments": STUDIO.substitutions()}


@api_app.get("/substitutions/{moment_id}")
def get_substitution(moment_id: str) -> dict[str, Any]:
    moment = STUDIO.substitution(moment_id)
    if not moment:
        raise HTTPException(status_code=404, detail="Unknown substitution moment")
    explained = EXPLAIN.explain_substitution(moment)
    return {
        **explained,
        "viewer_text": explained["narrative"],
        "mode": STUDIO.viewer.mode,
        "language": "en",
    }


@api_app.get("/shortlist/{alert_id}")
def shortlist_for_alert(alert_id: str, team_side: str | None = None) -> dict[str, Any]:
    return propose_roles_for_alert(alert_id, team_side=team_side, bench_only=True, limit=3)


@api_app.get("/agent/tools")
def list_agent_tools() -> dict[str, Any]:
    return {
        "tools": agent_tools.TOOL_SPECS,
        "agents": [
            {"key": s.key, "name": s.name, "role": s.role, "tools": list(s.tools)}
            for s in SPECIALISTS.values()
        ],
    }


@api_app.post("/agent/chat")
def chat_with_agent(body: dict[str, Any]) -> dict[str, Any]:
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message required")
    return agent_chat(message, engine=body.get("engine"), audience=body.get("audience") or "coach")


@api_app.post("/mcp")
async def mcp_endpoint(request: Request) -> Response:
    """MCP Streamable HTTP (JSON responses). Requires `Authorization: Bearer $PITCHPULSE_MCP_KEY`."""
    if not mcp_server.mcp_key():
        return JSONResponse({"error": "MCP over HTTP is disabled: set PITCHPULSE_MCP_KEY"}, 503)
    auth = request.headers.get("authorization") or request.headers.get("x-api-key")
    if not mcp_server.authorized(auth):
        return JSONResponse({"error": "unauthorized"}, 401,
                            headers={"WWW-Authenticate": 'Bearer realm="pitchpulse-mcp"'})
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse({"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32700, "message": "Parse error"}}, 400)
    if isinstance(payload, list):
        replies = [r for r in (await asyncio.to_thread(mcp_server.handle, m) for m in payload) if r]
        return JSONResponse(replies) if replies else Response(status_code=202)
    reply = await asyncio.to_thread(mcp_server.handle, payload)
    return JSONResponse(reply) if reply else Response(status_code=202)


@api_app.get("/mcp")
def mcp_stream_not_supported() -> Response:
    # No server-initiated stream: clients fall back to plain request/response.
    return Response(status_code=405, headers={"Allow": "POST"})


@api_app.get("/fan/live")
def fan_live_pitch(minute: float = 0.0) -> dict[str, Any]:
    """Live fan pitch: cumulative player stats + problems active at match minute."""
    match_id = STUDIO.match_id or "syn-001"
    if not (match_dir(match_id) / "events.jsonl").exists():
        raise HTTPException(status_code=404, detail=f"Match not found: {match_id}")
    st = SESSION.status()
    live_minute = float(minute)
    if st.loaded and st.match_minute and minute <= 0:
        live_minute = float(st.match_minute)
    return build_fan_live(match_id, live_minute)


@api_app.get("/fan/halftime")
def fan_halftime_summary() -> dict[str, Any]:
    """Living-room Match Day Summary — no live coaching feed."""
    match_id = STUDIO.match_id or "syn-001"
    if not (match_dir(match_id) / "events.jsonl").exists():
        raise HTTPException(status_code=404, detail=f"Match not found: {match_id}")
    summary = build_halftime_summary(match_id)
    cards = summary["cards"]
    return {
        **summary,
        "viewer": STUDIO.viewer.to_dict(),
        "localized": {
            "title": summary["title"],
            "access_note": summary["access"]["note"],
            "cold_start": cards["cold_start"],
            "defensive_pressure": cards["defensive_pressure"],
            "chance_conversion": cards["chance_conversion"],
            "cross_productivity": cards["cross_productivity"],
            "crowd_call": cards["crowd_call"],
            "charts": summary.get("charts"),
            "team_boards": summary.get("team_boards"),
            "problems": summary.get("problems"),
            "pitch_players": summary.get("pitch_players"),
        },
    }


@api_app.get("/recap")
def match_recap() -> dict[str, Any]:
    if not STUDIO.match_id:
        raise HTTPException(status_code=400, detail="Load a match first")
    alerts = []
    for a in STUDIO._expected_alerts:
        exp = EXPLAIN.explain_alert(
            alert_id=a["alert_id"],
            evidence={},
            match_minute=a.get("t_peak_ms", 0) / 60000.0,
            related_player_ids=a.get("related_player_ids"),
            use_llm=False,
        )
        alerts.append(
            {
                "alert_id": a["alert_id"],
                "leak_summary": a.get("leak_summary"),
                "personalized": EXPLAIN.for_viewer(exp, STUDIO.viewer),
            }
        )
    subs = [EXPLAIN.explain_substitution(s) for s in STUDIO.substitutions()]
    return {
        "match_id": STUDIO.match_id,
        "headline": "Recap: leaks, coaching reactions, and what changed after the substitutions.",
        "viewer": STUDIO.viewer.to_dict(),
        "alerts": alerts,
        "substitutions": [
            {
                "moment_id": s["moment_id"],
                "text": s["narrative"],
            }
            for s in subs
        ],
        "source": "template",
    }


def _enrich_sse_message(msg: dict[str, Any]) -> dict[str, Any]:
    if msg.get("type") != "alert":
        return msg
    payload = dict(msg.get("payload") or {})
    alert_id = payload.get("alert_id")
    if not alert_id:
        return msg
    explanation = EXPLAIN.explain_alert(
        alert_id=alert_id,
        evidence=payload.get("evidence") or {},
        match_minute=payload.get("match_minute"),
        related_player_ids=STUDIO.related_players(alert_id),
        use_llm=False,  # keep SSE fast; use POST /explain/alert for LLM
    )
    personalized = EXPLAIN.for_viewer(explanation, STUDIO.viewer)
    overlay = build_overlay_packet(
        alert_id=alert_id,
        t_ms=int(payload.get("t_ms") or 0),
        explanation=explanation,
        severity=str(payload.get("severity") or "warning"),
    )
    payload["personalized"] = personalized
    payload["overlay"] = overlay
    return {"type": "alert", "payload": payload}


async def _sse_generator():
    """Stream replay messages while session is running."""
    yield f"data: {json.dumps({'type': 'connected', 'payload': _status_dict(SESSION.status())})}\n\n"

    while True:
        messages, sleep_s, _has_more = SESSION.next_messages()
        if not messages:
            await asyncio.sleep(0.05)
            st = SESSION.status()
            if not st.running and st.index >= st.total_events and st.loaded:
                break
            continue

        for msg in messages:
            enriched = _enrich_sse_message(msg)
            yield f"data: {json.dumps(enriched, separators=(',', ':'))}\n\n"

        if sleep_s > 0:
            await asyncio.sleep(sleep_s)

        if any(m.get("type") == "done" for m in messages):
            break

    yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"


@api_app.get("/replay/stream")
async def replay_stream(speed: float = 120.0, autostart: bool = True) -> StreamingResponse:
    if not SESSION.status().loaded:
        raise HTTPException(status_code=400, detail="Load a match first: POST /replay/load")
    st = SESSION.status()
    if autostart and not st.running and st.index < st.total_events:
        SESSION.start(speed=max(0.0, speed))
    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _static_dir():
    """Return web/dist when present (Docker / single-port demo)."""
    import os
    from pathlib import Path

    env = os.environ.get("PITCHPULSE_STATIC", "").strip()
    candidates = []
    if env:
        candidates.append(Path(env))
    # src/pitchpulse/api/main.py → repo root
    candidates.append(Path(__file__).resolve().parents[3] / "web" / "dist")
    candidates.append(Path("/app/web/dist"))
    for path in candidates:
        if path.is_dir() and (path / "index.html").is_file():
            return path
    return None


def _build_app() -> FastAPI:
    """API-only in local/dev; API under /api + SPA at / when web/dist exists."""
    static = _static_dir()
    if static is None:
        return api_app

    from fastapi.staticfiles import StaticFiles

    root = FastAPI(title="PitchPulse AI", version="0.1.0")
    root.mount("/api", api_app)
    root.mount("/", StaticFiles(directory=str(static), html=True), name="ui")
    return root


# Load .env at import: a mounted sub-app's lifespan never runs, so the /api build would miss it.
load_dotenv()
app = _build_app()


def main() -> None:
    import os

    import uvicorn

    load_dotenv()
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("pitchpulse.api.main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()

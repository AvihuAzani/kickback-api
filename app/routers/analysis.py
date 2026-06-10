import json
import asyncio
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from ..services.auth import decode_token
from ..ai.analyzer import analyzer
from ..signaling import room_manager

router = APIRouter()

# Throttle: analyze max 1 frame per second per camera
_last_analysis: dict[str, float] = {}
ANALYSIS_INTERVAL = 1.5  # seconds

# ─── Event deduplication ─────────────────────────────────────────────────────
# Key: "{game_id}:{event_type}" → timestamp of last accepted event
_last_event: dict[str, float] = {}
DEDUP_WINDOW = 8.0  # seconds — same event type within this window = duplicate

class EventReport(BaseModel):
    event: str
    confidence: float
    description: str
    team: Optional[str] = None
    player: Optional[str] = None
    camera_position: str

security = HTTPBearer()

@router.post("/games/{game_id}/events")
async def report_event(
    game_id: str,
    body: EventReport,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Camera phones report detected AI events here. Backend deduplicates and broadcasts."""
    try:
        decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401)

    dedup_key = f"{game_id}:{body.event}"
    now = time.time()

    # Reject duplicates within the dedup window
    if now - _last_event.get(dedup_key, 0) < DEDUP_WINDOW:
        return {"accepted": False, "reason": "duplicate"}

    _last_event[dedup_key] = now

    event_msg = {
        "type": "ai_event",
        "event": body.event,
        "confidence": body.confidence,
        "description": body.description,
        "team": body.team,
        "player": body.player,
        "cameraPosition": body.camera_position,
    }

    # Broadcast to all monitor screens watching this game
    await room_manager.notify_monitors(game_id, event_msg)

    return {"accepted": True}


@router.websocket("/ws/analyze/{game_id}")
async def analyze_stream(
    websocket: WebSocket,
    game_id: str,
    token: str = Query(...),
    position: str = Query("C"),
    team_a: str = Query("Team A"),
    team_b: str = Query("Team B"),
    attack_dir: str = Query("left-to-right"),
):
    try:
        user_id = decode_token(token)
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    camera_key = f"{game_id}:{user_id}:{position}"
    import time

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg.get("type") != "frame":
                continue

            # Throttle
            now = time.time()
            last = _last_analysis.get(camera_key, 0)
            if now - last < ANALYSIS_INTERVAL:
                continue
            _last_analysis[camera_key] = now

            # Analyze in background — don't block frame ingestion
            asyncio.create_task(
                _analyze_and_broadcast(
                    game_id=game_id,
                    camera_key=camera_key,
                    frame_b64=msg["frame"],
                    position=position,
                    team_a=team_a,
                    team_b=team_b,
                    attack_dir=attack_dir,
                    ws=websocket,
                )
            )

    except WebSocketDisconnect:
        _last_analysis.pop(camera_key, None)


async def _analyze_and_broadcast(
    game_id: str,
    camera_key: str,
    frame_b64: str,
    position: str,
    team_a: str,
    team_b: str,
    attack_dir: str,
    ws: WebSocket,
):
    result = await analyzer.analyze_frame(
        frame_b64=frame_b64,
        camera_position=position,
        team_a_name=team_a,
        team_b_name=team_b,
        attack_direction=attack_dir,
    )

    if result.get("event") == "NONE":
        return

    if result.get("confidence", 0) < 0.8:
        return

    event_msg = {
        "type": "ai_event",
        "cameraPosition": position,
        **result,
    }

    # Send back to the camera client
    try:
        await ws.send_text(json.dumps(event_msg))
    except Exception:
        pass

    # Broadcast to all monitors watching this game
    await room_manager.notify_monitors(game_id, event_msg)

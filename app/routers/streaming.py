import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ..services.auth import decode_token
from ..signaling import room_manager

router = APIRouter()


@router.websocket("/ws/camera/{game_id}")
async def camera_stream(
    websocket: WebSocket,
    game_id: str,
    token: str = Query(...),
    position: str = Query("C"),
):
    # Validate token
    try:
        user_id = decode_token(token)
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    camera_id = f"{user_id}:{position}"
    await room_manager.add_camera(game_id, camera_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "offer":
                # Create a lightweight SDP answer (passthrough for now —
                # in production this would go to a media server like mediasoup)
                answer_sdp = _build_answer(msg["sdp"])
                await websocket.send_text(json.dumps({
                    "type": "answer",
                    "sdp": answer_sdp,
                }))
                # Notify monitor clients that a new camera joined
                await room_manager.notify_monitors(game_id, {
                    "type": "camera_joined",
                    "cameraId": camera_id,
                    "position": position,
                    "gameId": game_id,
                })

            elif msg_type == "ice":
                # Forward ICE candidates to monitor (future: to media server)
                pass

    except WebSocketDisconnect:
        await room_manager.remove_camera(game_id, camera_id)
        await room_manager.notify_monitors(game_id, {
            "type": "camera_left",
            "cameraId": camera_id,
            "position": position,
        })


@router.websocket("/ws/monitor/{game_id}")
async def monitor_stream(
    websocket: WebSocket,
    game_id: str,
    token: str = Query(...),
):
    try:
        decode_token(token)
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    await room_manager.add_monitor(game_id, websocket)

    # Send current camera list
    cameras = room_manager.get_cameras(game_id)
    await websocket.send_text(json.dumps({
        "type": "cameras_list",
        "cameras": cameras,
    }))

    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        await room_manager.remove_monitor(game_id, websocket)


def _build_answer(offer_sdp: str) -> str:
    """
    Minimal SDP answer — replaces sendrecv/sendonly with recvonly.
    In production, replace this with a real media server (mediasoup / LiveKit).
    """
    lines = []
    for line in offer_sdp.splitlines():
        if line.startswith("a=sendrecv") or line.startswith("a=sendonly"):
            lines.append("a=recvonly")
        else:
            lines.append(line)
    return "\r\n".join(lines)

import json
import asyncio
from fastapi import WebSocket
from typing import Dict, Set, List


class RoomManager:
    def __init__(self):
        # game_id -> {camera_id: WebSocket}
        self._cameras: Dict[str, Dict[str, WebSocket]] = {}
        # game_id -> set of monitor WebSockets
        self._monitors: Dict[str, Set[WebSocket]] = {}

    async def add_camera(self, game_id: str, camera_id: str, ws: WebSocket):
        if game_id not in self._cameras:
            self._cameras[game_id] = {}
        self._cameras[game_id][camera_id] = ws

    async def remove_camera(self, game_id: str, camera_id: str):
        if game_id in self._cameras:
            self._cameras[game_id].pop(camera_id, None)

    async def add_monitor(self, game_id: str, ws: WebSocket):
        if game_id not in self._monitors:
            self._monitors[game_id] = set()
        self._monitors[game_id].add(ws)

    async def remove_monitor(self, game_id: str, ws: WebSocket):
        if game_id in self._monitors:
            self._monitors[game_id].discard(ws)

    def get_cameras(self, game_id: str) -> List[str]:
        return list(self._cameras.get(game_id, {}).keys())

    async def notify_monitors(self, game_id: str, message: dict):
        dead = set()
        for ws in self._monitors.get(game_id, set()):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._monitors[game_id].discard(ws)


room_manager = RoomManager()

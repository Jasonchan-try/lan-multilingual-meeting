import json
from collections import defaultdict
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.message import Message
from app.services.meeting_service import meeting_service
from app.services.translation_service import TranslationService

router = APIRouter()
translation_service = TranslationService()


class WSManager:
    def __init__(self) -> None:
        self.connections: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, room_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.connections[room_id].add(ws)

    def disconnect(self, room_id: str, ws: WebSocket) -> None:
        self.connections[room_id].discard(ws)

    async def broadcast(self, room_id: str, payload: dict) -> None:
        to_remove = []
        for ws in self.connections[room_id]:
            try:
                await ws.send_text(json.dumps(payload, ensure_ascii=False))
            except Exception:
                to_remove.append(ws)
        for ws in to_remove:
            self.connections[room_id].discard(ws)


ws_manager = WSManager()


@router.websocket("/ws/{participant_id}")
async def room_ws(websocket: WebSocket, participant_id: str):
    meeting = meeting_service.get_meeting()
    if not meeting:
        await websocket.close(code=4001)
        return
    room_id = meeting.room_id
    await ws_manager.connect(room_id, websocket)
    try:
        await ws_manager.broadcast(room_id, {"type": "system", "text": "有成员进入会议", "online": meeting.online_count})
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            current = meeting_service.get_meeting()
            if not current:
                await ws_manager.broadcast(room_id, {"type": "system", "text": "会议已结束"})
                break

            if data.get("type") == "chat":
                msg = Message(
                    sender_id=participant_id,
                    sender_name=data.get("sender_name", "匿名"),
                    sender_language=data.get("sender_language", "zh"),
                    original_text=data.get("text", ""),
                )
                if current.translation_enabled:
                    msg.translated_text = translation_service.translate_bi(msg.original_text, msg.sender_language)
                meeting_service.post_message(msg)
                await ws_manager.broadcast(
                    room_id,
                    {
                        "type": "chat",
                        "sender_name": msg.sender_name,
                        "sender_language": msg.sender_language,
                        "original_text": msg.original_text,
                        "translated_text": msg.translated_text,
                        "timestamp": msg.timestamp,
                    },
                )
    except WebSocketDisconnect:
        meeting_service.set_offline(participant_id)
    except Exception as exc:
        # Keep server alive and expose traceback context in terminal for debugging.
        print(f"WebSocket error for participant {participant_id}: {exc}")
    finally:
        ws_manager.disconnect(room_id, websocket)

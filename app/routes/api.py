from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings
from app.models.message import Message
from app.services.cleanup_service import CleanupService
from app.services.meeting_service import meeting_service
from app.services.qr_service import generate_qr_data_url
from app.services.summary_service import SummaryService
from app.services.translation_service import TranslationService
from app.utils.network import get_lan_ip

router = APIRouter(prefix="/api")
summary_service = SummaryService()
translation_service = TranslationService()


class JoinRequest(BaseModel):
    meeting_code: str
    nickname: str
    language: str
    participant_id: str


class SettingsRequest(BaseModel):
    translation_enabled: bool
    summary_language: str
    meeting_name: str


class PostMessageRequest(BaseModel):
    room_id: str
    participant_id: str
    sender_name: str
    sender_language: str
    text: str


def _get_active_meeting():
    meeting = meeting_service.get_meeting()
    if not meeting or meeting.dissolved:
        raise HTTPException(status_code=404, detail="会议不存在")
    return meeting


def _validate_room_and_participant(room_id: str, participant_id: str):
    meeting = _get_active_meeting()
    if meeting.room_id != room_id:
        raise HTTPException(status_code=403, detail="会议已结束，请重新加入")
    if participant_id not in meeting.participants:
        raise HTTPException(status_code=403, detail="成员不属于当前会议")
    return meeting


@router.post("/meeting/init")
async def init_meeting():
    meeting = meeting_service.get_meeting()
    if not meeting:
        raise HTTPException(status_code=404, detail="当前没有进行中的会议")
    return _meeting_payload(meeting)


@router.post("/meeting/create")
async def create_meeting():
    meeting = meeting_service.create_meeting()
    return _meeting_payload(meeting)


def _meeting_payload(meeting):
    lan = get_lan_ip()
    url = f"http://{lan}:{settings.port}/join"
    return {
        "room_id": meeting.room_id,
        "meeting_code": meeting.meeting_code,
        "meeting_name": meeting.meeting_name,
        "translation_enabled": meeting.translation_enabled,
        "summary_language": meeting.summary_language,
        "online_count": meeting.online_count,
        "join_url": url,
        "qr_data_url": generate_qr_data_url(f"{url}?code={meeting.meeting_code}"),
    }


@router.get("/meeting/status")
async def meeting_status():
    meeting = _get_active_meeting()
    return {
        "room_id": meeting.room_id,
        "meeting_name": meeting.meeting_name,
        "meeting_code": meeting.meeting_code,
        "translation_enabled": meeting.translation_enabled,
        "summary_language": meeting.summary_language,
        "online_count": meeting.online_count,
        "participants": [p.__dict__ for p in meeting.participants.values()],
        "dissolved": meeting.dissolved,
    }


@router.post("/meeting/join")
async def join_meeting(payload: JoinRequest):
    meeting = _get_active_meeting()
    if payload.meeting_code != meeting.meeting_code:
        raise HTTPException(status_code=400, detail="会议码错误")
    p = meeting_service.add_participant(payload.participant_id, payload.nickname, payload.language)
    if not p:
        raise HTTPException(status_code=400, detail="加入失败")
    return {"ok": True, "room_id": meeting.room_id}


@router.post("/meeting/message")
async def post_message(payload: PostMessageRequest):
    meeting = _validate_room_and_participant(payload.room_id, payload.participant_id)
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="消息不能为空")

    msg = Message(
        sender_id=payload.participant_id,
        sender_name=payload.sender_name or "匿名",
        sender_language=payload.sender_language or "zh",
        original_text=text,
    )
    print(
        "AI translation status:",
        {
            "meeting_translation_enabled": meeting.translation_enabled,
            **translation_service.diagnostics(),
        },
    )
    if meeting.translation_enabled:
        msg.translated_text = translation_service.translate_bi(msg.original_text, msg.sender_language)
    meeting_service.post_message(msg)
    return {
        "ok": True,
        "message": {
            "sender_name": msg.sender_name,
            "sender_language": msg.sender_language,
            "original_text": msg.original_text,
            "translated_text": msg.translated_text,
            "timestamp": msg.timestamp,
        },
    }


@router.get("/meeting/messages")
async def get_messages(
    room_id: str | None = None,
    participant_id: str | None = None,
    from_index: int = 0,
    tail: int = 0,
):
    if not room_id or not participant_id:
        return {"messages": [], "next_index": max(from_index, 0), "inactive": True}
    meeting = _validate_room_and_participant(room_id, participant_id)
    total = len(meeting.messages)

    if tail > 0:
        start = max(0, total - min(tail, 200))
        sliced = meeting.messages[start:]
    else:
        if from_index < 0:
            from_index = 0
        sliced = meeting.messages[from_index:]
    data = [
        {
            "sender_name": m.sender_name,
            "sender_language": m.sender_language,
            "original_text": m.original_text,
            "translated_text": m.translated_text,
            "timestamp": m.timestamp,
        }
        for m in sliced
    ]
    return {"messages": data, "next_index": total}


@router.post("/meeting/settings")
async def update_settings(payload: SettingsRequest):
    meeting_service.update_settings(payload.translation_enabled, payload.summary_language, payload.meeting_name)
    return {"ok": True}


@router.post("/meeting/summary")
async def make_summary():
    meeting = meeting_service.get_meeting()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    text = summary_service.generate_summary(meeting)
    meeting.summary_text = text
    return {"summary": text}


@router.get("/meeting/summary/download")
async def download_summary(fmt: str = "md"):
    meeting = meeting_service.get_meeting()
    if not meeting or not meeting.summary_text:
        raise HTTPException(status_code=404, detail="暂无纪要")
    ext = "txt" if fmt == "txt" else "md"
    p = CleanupService.write_summary_file(meeting.room_id, meeting.summary_text, ext)
    media = "text/plain"
    return FileResponse(path=p, media_type=media, filename=f"meeting_summary.{ext}")


@router.post("/meeting/dissolve")
async def dissolve_meeting():
    meeting_service.dissolve()
    CleanupService.clean_temp_dir()
    return {"ok": True}

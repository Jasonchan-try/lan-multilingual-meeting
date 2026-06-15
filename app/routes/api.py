import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings, TEMP_DIR
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

# 允许上传的扩展名
ALLOWED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp',  # 图片
    '.txt',                                     # 纯文本
    '.pdf', '.docx', '.xlsx', '.zip', '.csv',  # 其他可下载类型
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


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
    text: str = ''
    attachment_url: str | None = None
    attachment_name: str | None = None
    attachment_type: str | None = None
    attachment_size: int | None = None
    attachment_text: str | None = None


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


@router.post("/meeting/upload")
async def upload_file(
    file: UploadFile = File(...),
    room_id: str = Form(...),
    participant_id: str = Form(...),
):
    """上传附件，返回访问 URL 及元信息"""
    _validate_room_and_participant(room_id, participant_id)

    # 校验扩展名
    original_name = file.filename or 'file'
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型：{suffix}")

    # 读取内容并校验大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件不能超过 10MB")

    # 判断类型
    if suffix in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}:
        file_type = 'image'
    elif suffix == '.txt':
        file_type = 'text'
    else:
        file_type = 'other'

    # 存到 temp 目录，用 uuid 避免文件名冲突
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    save_path = TEMP_DIR / safe_name
    save_path.write_bytes(content)

    # txt 文件读取前 2000 字符供聊天内预览
    text_content = None
    if file_type == 'text':
        try:
            text_content = content.decode('utf-8', errors='replace')[:2000]
        except Exception:
            text_content = None

    file_url = f"/api/meeting/file/{safe_name}"
    return {
        "url": file_url,
        "filename": safe_name,
        "original_name": original_name,
        "file_type": file_type,
        "file_size": len(content),
        "text_content": text_content,
    }


@router.get("/meeting/file/{filename}")
async def serve_file(filename: str):
    """提供附件的访问/下载"""
    # 防止路径穿越
    safe = Path(filename).name
    file_path = TEMP_DIR / safe
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    return FileResponse(path=file_path, filename=safe)


@router.post("/meeting/message")
async def post_message(payload: PostMessageRequest):
    meeting = _validate_room_and_participant(payload.room_id, payload.participant_id)
    text = payload.text.strip()

    # 文字和附件至少有一个
    if not text and not payload.attachment_url:
        raise HTTPException(status_code=400, detail="消息不能为空")

    msg = Message(
        sender_id=payload.participant_id,
        sender_name=payload.sender_name or "匿名",
        sender_language=payload.sender_language or "zh",
        original_text=text,
        attachment_url=payload.attachment_url,
        attachment_name=payload.attachment_name,
        attachment_type=payload.attachment_type,
        attachment_size=payload.attachment_size,
        attachment_text=payload.attachment_text,
    )

    # ✅ 先入库，前端 poll 可立即看到消息
    meeting_service.post_message(msg)

    # 再翻译（仅对文字内容翻译，附件不翻译）
    print(
        "AI translation status:",
        {
            "meeting_translation_enabled": meeting.translation_enabled,
            **translation_service.diagnostics(),
        },
    )
    if meeting.translation_enabled and text:
        msg.translated_text = translation_service.translate_bi(msg.original_text, msg.sender_language)

    return {
        "ok": True,
        "message": {
            "sender_name": msg.sender_name,
            "sender_language": msg.sender_language,
            "original_text": msg.original_text,
            "translated_text": msg.translated_text,
            "timestamp": msg.timestamp,
            "attachment_url": msg.attachment_url,
            "attachment_name": msg.attachment_name,
            "attachment_type": msg.attachment_type,
            "attachment_size": msg.attachment_size,
            "attachment_text": msg.attachment_text,
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
            "attachment_url": m.attachment_url,
            "attachment_name": m.attachment_name,
            "attachment_type": m.attachment_type,
            "attachment_size": m.attachment_size,
            "attachment_text": m.attachment_text,
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

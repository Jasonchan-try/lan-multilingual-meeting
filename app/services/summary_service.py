from openai import OpenAI

from app.config import settings
from app.models.meeting import Meeting


class SummaryService:
    def __init__(self) -> None:
        self.enabled = bool(settings.openai_api_key)
        self.client = None
        if self.enabled:
            self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        print(
            "AI summary init:",
            {
                "openai_api_key_loaded": bool(settings.openai_api_key),
                "summary_service_enabled": self.enabled,
                "summary_model": settings.effective_summary_model,
                "openai_base_url": settings.openai_base_url,
            },
        )

    def generate_summary(self, meeting: Meeting) -> str:
        participants = ", ".join([p.nickname for p in meeting.participants.values()]) or "无"
        transcript = []
        for m in meeting.messages:
            if m.translated_text:
                transcript.append(f"[{m.timestamp}] {m.sender_name}: {m.original_text} / 译: {m.translated_text}")
            else:
                transcript.append(f"[{m.timestamp}] {m.sender_name}: {m.original_text}")
        transcript_text = "\n".join(transcript) if transcript else "暂无聊天记录"

        if not self.enabled or self.client is None:
            print(
                "AI summary fallback:",
                {
                    "openai_api_key_loaded": bool(settings.openai_api_key),
                    "summary_service_enabled": self.enabled,
                    "client_ready": self.client is not None,
                },
            )
            return self._fallback_summary(meeting.meeting_name, participants, transcript_text)

        language_hint = "中文" if meeting.summary_language == "zh" else "日语"
        prompt = f"""
请根据以下会议聊天记录生成结构化会议纪要，语言使用{language_hint}。
必须包含：
1. 会议标题
2. 会议时间
3. 参会人员
4. 主要讨论内容
5. 已确认事项
6. 待办事项
7. 风险/问题点

会议标题：{meeting.meeting_name}
会议时间：{meeting.created_at.strftime('%Y-%m-%d %H:%M:%S')}
参会人员：{participants}
聊天记录：
{transcript_text}
"""
        try:
            print(
                "AI summary request:",
                {
                    "summary_language": meeting.summary_language,
                    "message_count": len(meeting.messages),
                    "model": settings.effective_summary_model,
                },
            )
            resp = self.client.chat.completions.create(
                model=settings.effective_summary_model,
                messages=[
                    {"role": "system", "content": "你是专业会议纪要助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            print("AI summary failed:", repr(exc))
            return "纪要生成失败，请稍后重试。"

    def _fallback_summary(self, title: str, participants: str, transcript: str) -> str:
        return (
            f"# 会议纪要\n\n"
            f"- 会议标题：{title}\n"
            f"- 会议时间：自动生成时刻\n"
            f"- 参会人员：{participants}\n\n"
            f"## 主要讨论内容\n"
            f"{transcript[:1500]}\n\n"
            f"## 已确认事项\n- 待补充\n\n"
            f"## 待办事项\n- 待补充\n\n"
            f"## 风险/问题点\n- 待补充\n"
        )

import secrets
import string
from typing import Dict, Optional

from app.models.meeting import Meeting
from app.models.message import Message
from app.models.participant import Participant


class MeetingService:
    def __init__(self) -> None:
        self.current_meeting: Optional[Meeting] = None

    def create_meeting(self, meeting_name: str = "临时AI会议") -> Meeting:
        room_id = secrets.token_hex(8)
        code = "".join(secrets.choice(string.digits) for _ in range(6))
        self.current_meeting = Meeting(room_id=room_id, meeting_code=code, meeting_name=meeting_name)
        return self.current_meeting

    def get_meeting(self) -> Optional[Meeting]:
        return self.current_meeting

    def add_participant(self, participant_id: str, nickname: str, language: str, role: str = "participant") -> Optional[Participant]:
        meeting = self.current_meeting
        if not meeting or meeting.dissolved:
            return None
        p = Participant(participant_id=participant_id, nickname=nickname, language=language, role=role)
        meeting.participants[participant_id] = p
        return p

    def set_offline(self, participant_id: str) -> None:
        meeting = self.current_meeting
        if meeting and participant_id in meeting.participants:
            meeting.participants[participant_id].online = False

    def post_message(self, message: Message) -> bool:
        meeting = self.current_meeting
        if not meeting or meeting.dissolved:
            return False
        meeting.messages.append(message)
        return True

    def update_settings(self, translation_enabled: bool, summary_language: str, meeting_name: str) -> None:
        meeting = self.current_meeting
        if meeting and not meeting.dissolved:
            meeting.translation_enabled = translation_enabled
            meeting.summary_language = summary_language
            meeting.meeting_name = meeting_name

    def dissolve(self) -> None:
        if self.current_meeting:
            self.current_meeting.dissolved = True
            self.current_meeting.participants.clear()
            self.current_meeting.messages.clear()
            self.current_meeting.summary_text = None
            self.current_meeting = None


meeting_service = MeetingService()

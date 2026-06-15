from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from app.models.message import Message
from app.models.participant import Participant


@dataclass
class Meeting:
    room_id: str
    meeting_code: str
    meeting_name: str
    translation_enabled: bool = True
    summary_language: str = "zh"
    created_at: datetime = field(default_factory=datetime.now)
    participants: Dict[str, Participant] = field(default_factory=dict)
    messages: List[Message] = field(default_factory=list)
    summary_text: Optional[str] = None
    dissolved: bool = False

    @property
    def online_count(self) -> int:
        return sum(1 for p in self.participants.values() if p.online)

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Message:
    sender_id: str
    sender_name: str
    sender_language: str
    original_text: str
    translated_text: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

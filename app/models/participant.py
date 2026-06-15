from dataclasses import dataclass


@dataclass
class Participant:
    participant_id: str
    nickname: str
    language: str
    role: str = "participant"
    online: bool = True

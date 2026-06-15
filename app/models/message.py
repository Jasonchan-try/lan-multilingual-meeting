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
    # 附件字段
    attachment_url: Optional[str] = None       # 访问/下载 URL
    attachment_name: Optional[str] = None      # 原始文件名
    attachment_type: Optional[str] = None      # image / text / other
    attachment_size: Optional[int] = None      # 文件大小（字节）
    attachment_text: Optional[str] = None      # txt 文件的文本内容（前 2000 字符）

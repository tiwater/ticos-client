from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    id: Optional[str] = None
    role: MessageRole
    content: str
    item_id: Optional[str] = None  # Added item_id field for tracking conversation items
    user_id: str = "nobody"  # User identifier, default to "nobody"
    datetime: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class Memory(BaseModel):
    id: Optional[int] = None
    type: MemoryType
    content: str
    user_id: str = "nobody"  # User identifier, default to "nobody"
    datetime: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


class MessageRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


class MessageResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class MessagesResponse(MessageResponse):
    data: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int

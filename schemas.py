from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class NIMUsageLog(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    latency_sec: float
    endpoint: str  # e.g. 'chat', 'asr', 'tts'
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

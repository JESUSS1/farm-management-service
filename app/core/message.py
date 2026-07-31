from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MessageType(Enum):
    SENSOR_READING = "sensor_reading"
    COMMAND = "command"
    EVENT = "event"
    ERROR = "error"
    STATUS_RESPONSE = "status_response"
    REGISTRATION = "registration"


@dataclass
class Message:
    type: MessageType
    device_id: str
    payload: dict
    timestamp: datetime = field(default_factory=datetime.now)
    raw: Optional[str] = None

from abc import ABC, abstractmethod

from app.core.message import Message


class Handler(ABC):
    @abstractmethod
    async def handle(self, message: Message) -> bool:
        ...

from abc import ABC, abstractmethod

from app.core.message import Message


class Transport(ABC):
    @abstractmethod
    async def start(self):
        ...

    @abstractmethod
    async def stop(self):
        ...

    @abstractmethod
    async def send(self, device_id: str, message: Message) -> bool:
        ...

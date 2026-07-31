import asyncio
import logging

from app.core.message import Message
from app.transports.base import Transport

logger = logging.getLogger(__name__)


class TcpClientTransport(Transport):
    async def start(self):
        logger.info("TCP Client transport ready")

    async def stop(self):
        logger.info("TCP Client transport stopped")

    async def send(self, device_id: str, message: Message) -> bool:
        ip = message.payload.get("ip")
        port = message.payload.get("port")
        comando = message.payload.get("comando")
        if not all([ip, port, comando]):
            logger.error("Missing ip/port/comando in message payload")
            return False
        ip_limpia = ip.split("/")[0]
        writer = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip_limpia, port),
                timeout=5,
            )
            writer.write((comando + "\n").encode())
            await asyncio.wait_for(writer.drain(), timeout=3)
            logger.info("[WiFi] %s:%s <- %s", ip_limpia, port, comando)
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            logger.error("[WiFi] Error enviando a %s:%s: %s", ip_limpia, port, e)
            return False
        except Exception as e:
            logger.error(
                "[WiFi] Error inesperado a %s:%s: %s", ip_limpia, port, e, exc_info=True
            )
            return False
        finally:
            if writer:
                try:
                    writer.close()
                    await asyncio.wait_for(writer.wait_closed(), timeout=2)
                except Exception:
                    pass

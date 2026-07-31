import asyncio
import logging

from app.config import WIFI_SERVER_HOST, WIFI_SERVER_PORT
from app.transports.base import Transport

logger = logging.getLogger(__name__)


class TcpServerTransport(Transport):
    def __init__(self, on_message=None, max_clients=50):
        self._host = WIFI_SERVER_HOST
        self._port = WIFI_SERVER_PORT
        self._server = None
        self._on_message = on_message
        self._max_clients = max_clients
        self._clients: set[asyncio.Task] = set()

    async def start(self):
        self._server = await asyncio.start_server(
            self._on_connect,
            host=self._host,
            port=self._port,
        )
        logger.info("TCP Server listening on %s:%s", self._host, self._port)

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        for task in list(self._clients):
            task.cancel()
        if self._clients:
            await asyncio.wait(self._clients, timeout=5)
        logger.info("TCP Server stopped")

    async def send(self, device_id: str, message: Message) -> bool:
        raise NotImplementedError(
            "TcpServerTransport does not send, use TcpClientTransport"
        )

    async def _on_connect(self, reader, writer):
        if len(self._clients) >= self._max_clients:
            addr = writer.get_extra_info("peername")
            logger.warning("Limite de conexiones alcanzado, rechazando %s", addr)
            writer.close()
            return
        task = asyncio.current_task()
        self._clients.add(task)
        try:
            await self._handle_client(reader, writer)
        finally:
            self._clients.discard(task)

    async def _handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        logger.info("Nueva conexion desde %s", addr)
        try:
            while True:
                linea = await asyncio.wait_for(reader.readline(), timeout=60)
                if not linea:
                    break
                texto = linea.decode(errors="ignore").strip()
                if not texto:
                    continue
                logger.info("Dato recibido de %s: %s", addr, texto)
                if self._on_message:
                    respuesta = await self._on_message(texto, addr)
                    if respuesta:
                        writer.write((respuesta + "\n").encode())
                        await writer.drain()
        except asyncio.TimeoutError:
            logger.debug("Timeout en conexion %s", addr)
        except (ConnectionResetError, ConnectionAbortedError) as e:
            logger.debug("Conexion %s cerrada: %s", addr, e)
        except asyncio.CancelledError:
            logger.debug("Conexion %s cancelada por shutdown", addr)
        except Exception as e:
            logger.error(
                "Error en conexion %s: %s", addr, e, exc_info=True
            )
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.info("Conexion cerrada %s", addr)

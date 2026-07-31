import asyncio
import logging
from dataclasses import dataclass

from app.core.http_client import HttpClient
from app.core.message import Message, MessageType
from app.core.registry import DeviceRegistry
from app.handlers.sensor_handler import SensorHandler
from app.handlers.command_handler import CommandHandler
from app.protocol.decoder import decode_sensor_line
from app.transports.tcp_server import TcpServerTransport
from app.transports.tcp_client import TcpClientTransport

logger = logging.getLogger(__name__)

REINTENTO_BACKOFF = [5, 15, 45, 135, 405]


@dataclass
class RetryItem:
    device_key: str
    accion: str
    intento: int = 0


class Engine:
    def __init__(self):
        self._http = HttpClient()
        self._registry = DeviceRegistry(self._http)
        self._tcp_client = TcpClientTransport()
        self._tcp_server = None
        self._sensor_handler = None
        self._command_handler = None
        self._running = False
        self._retry_queue: asyncio.Queue[RetryItem] = asyncio.Queue()
        self._retry_task: asyncio.Task | None = None

    async def start(self):
        await self._http.start()
        await self._registry.refresh()
        logger.info(
            "Registry cargado: %d dispositivos", len(self._registry.get_all())
        )

        self._sensor_handler = SensorHandler(self._http)
        self._command_handler = CommandHandler(
            self._registry, self._tcp_client, self._http
        )

        await self._sensor_handler.start()

        self._tcp_server = TcpServerTransport(on_message=self._on_raw_message)
        await self._tcp_client.start()
        await self._tcp_server.start()

        self._retry_task = asyncio.create_task(self._retry_worker())

        self._running = True
        logger.info("Engine started")

    async def stop(self):
        self._running = False
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        await self._tcp_server.stop()
        await self._tcp_client.stop()
        await self._sensor_handler.stop()
        await self._http.stop()
        logger.info("Engine stopped")

    async def _on_raw_message(self, texto: str, addr):
        message = decode_sensor_line(texto)
        if message is None:
            logger.debug("Mensaje no reconocido desde %s: %s", addr, texto)
            return
        if message.type == MessageType.SENSOR_READING:
            await self._sensor_handler.handle(message)
        elif message.type == MessageType.EVENT:
            logger.info("Evento desde %s: %s", message.device_id, message.payload)
        elif message.type == MessageType.ERROR:
            logger.warning(
                "Error desde %s: %s (sensor: %s)",
                message.device_id,
                message.payload.get("error"),
                message.payload.get("contexto"),
            )
        elif message.type == MessageType.STATUS_RESPONSE:
            logger.info("Status desde %s: %s", message.device_id, message.payload)
        elif message.type == MessageType.REGISTRATION:
            mac = message.device_id
            logger.info("Registro solicitado desde %s, MAC: %s", addr[0], mac)
            row = await self._http.get_device_by_mac(mac)
            if row:
                await self._http.update_device_ip(row["dispositivo_id"], addr[0])
                await self._registry.refresh()
                logger.info(
                    "Dispositivo registrado: %s (%s) desde %s",
                    row["device_key"], mac, addr[0],
                )
                return f"DEVICE_KEY:{row['device_key']};"
            else:
                logger.warning(
                    "MAC desconocida intentando registrarse: %s desde %s",
                    mac, addr[0],
                )
                return "ERROR:UNKNOWN_MAC;"

    async def send_command(self, device_key: str, accion: str) -> bool:
        message = Message(
            type=MessageType.COMMAND,
            device_id=device_key,
            payload={"accion": accion},
        )
        ok = await self._command_handler.handle(message)
        if not ok:
            self._retry_queue.put_nowait(RetryItem(device_key=device_key, accion=accion))
        return ok

    async def _retry_worker(self):
        logger.info("Retry worker iniciado (backoff: %s)", REINTENTO_BACKOFF)
        while True:
            try:
                item = await self._retry_queue.get()
            except asyncio.CancelledError:
                break
            delay = REINTENTO_BACKOFF[item.intento] if item.intento < len(REINTENTO_BACKOFF) else REINTENTO_BACKOFF[-1]
            await asyncio.sleep(delay)

            try:
                message = Message(
                    type=MessageType.COMMAND,
                    device_id=item.device_key,
                    payload={"accion": item.accion},
                )
                ok = await self._command_handler.handle(message)
                if ok:
                    logger.info(
                        "[RETRY OK] %s -> %s (intento %d)",
                        item.device_key,
                        item.accion,
                        item.intento + 1,
                    )
                else:
                    item.intento += 1
                    if item.intento < len(REINTENTO_BACKOFF):
                        self._retry_queue.put_nowait(item)
                    else:
                        logger.error(
                            "[RETRY AGOTADO] %s -> %s: maximos reintentos alcanzados",
                            item.device_key,
                            item.accion,
                        )
            except Exception as e:
                logger.error(
                    "[RETRY ERROR] %s -> %s: %s",
                    item.device_key,
                    item.accion,
                    e,
                    exc_info=True,
                )

    async def refresh_registry(self):
        await self._registry.refresh()

    @property
    def registry(self):
        return self._registry

    @property
    def http(self):
        return self._http

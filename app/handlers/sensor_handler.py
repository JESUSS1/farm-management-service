import asyncio
import logging
import time

from app.core.http_client import HttpClient
from app.core.message import Message, MessageType
from app.handlers.base import Handler

logger = logging.getLogger(__name__)

LIMITE_FALLOS_SENSOR = 20
VENTANA_FALLOS_SENSOR = 600


class SensorHandler(Handler):
    def __init__(self, http: HttpClient, max_queue=1000, flush_interval=2, flush_batch=50):
        self._http = http
        self._queue: asyncio.Queue[Message] = asyncio.Queue(maxsize=max_queue)
        self._flush_interval = flush_interval
        self._flush_batch = flush_batch
        self._flush_task: asyncio.Task | None = None
        self._running = False
        self._device_failures: dict[str, int] = {}
        self._device_first_fail: dict[str, float] = {}
        self._device_incidencia_logged: dict[str, bool] = {}
        self._device_dispositivo_id: dict[str, int] = {}

    async def start(self):
        self._running = True
        self._device_failures.clear()
        self._device_first_fail.clear()
        self._device_incidencia_logged.clear()
        self._device_dispositivo_id.clear()
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(
            "SensorHandler iniciado (queue=%d, flush_interval=%ds, batch=%d)",
            self._queue.maxsize,
            self._flush_interval,
            self._flush_batch,
        )

    async def stop(self):
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush()
        logger.info("SensorHandler detenido, cola drenada")

    async def handle(self, message: Message) -> bool:
        if message.type != MessageType.SENSOR_READING:
            return False
        try:
            self._queue.put_nowait(message)
            return True
        except asyncio.QueueFull:
            logger.warning(
                "Cola de lecturas llena (%d), descartando: %s/%s",
                self._queue.maxsize,
                message.device_id,
                message.payload.get("variable"),
            )
            return False

    async def _flush_loop(self):
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval)
                if not self._queue.empty():
                    await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error en flush loop: %s", e, exc_info=True)

    async def _flush(self):
        if self._queue.empty():
            return
        batch: list[Message] = []
        while not self._queue.empty() and len(batch) < self._flush_batch:
            try:
                batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        if not batch:
            return

        readings = []
        for msg in batch:
            payload = msg.payload
            readings.append({
                "device_id": msg.device_id,
                "parent_device": payload.get("parent_device", ""),
                "variable": payload.get("variable", ""),
                "valor": payload.get("valor"),
                "unidad": payload.get("unidad", ""),
                "firmware_version": payload.get("firmware_version", ""),
                "raw": msg.raw or "",
            })

        try:
            saved = await self._http.post_readings_batch(readings)
            if saved > 0:
                for msg in batch:
                    device_key = msg.device_id
                    self._limpiar_device(device_key)
                logger.info("Flushed %d lecturas a backend", saved)
            else:
                for msg in batch:
                    device_key = msg.device_id
                    self._device_failures[device_key] = (
                        self._device_failures.get(device_key, 0) + 1
                    )
                    await self._incrementar_fallo(msg)
        except Exception as e:
            logger.error(
                "Error enviando batch al backend, re-encolando %d lecturas: %s",
                len(batch),
                e,
                exc_info=True,
            )
            for msg in batch:
                device_key = msg.device_id
                self._device_failures[device_key] = (
                    self._device_failures.get(device_key, 0) + 1
                )
                await self._incrementar_fallo(msg)
                try:
                    self._queue.put_nowait(msg)
                except asyncio.QueueFull:
                    logger.warning("Cola llena, lectura descartada en re-encolado")
                    break

    async def _incrementar_fallo(self, msg: Message):
        device_key = msg.device_id
        counter = self._device_failures.get(device_key, 0)

        if self._device_first_fail.get(device_key, 0.0) == 0.0:
            self._device_first_fail[device_key] = time.monotonic()

        if counter < LIMITE_FALLOS_SENSOR:
            return

        if self._device_incidencia_logged.get(device_key):
            return

        elapsed = time.monotonic() - self._device_first_fail[device_key]
        if elapsed > VENTANA_FALLOS_SENSOR:
            self._device_failures[device_key] = 1
            self._device_first_fail[device_key] = time.monotonic()
            return

        dispositivo_id = self._device_dispositivo_id.get(device_key)
        self._device_incidencia_logged[device_key] = True

        try:
            await self._http.create_incident(
                "ERROR_SENSOR",
                dispositivo_id,
                device_key,
                f"No se pudieron guardar lecturas de {device_key} tras {LIMITE_FALLOS_SENSOR} intentos consecutivos",
                {"fallos_consecutivos": counter, "ultima_variable": msg.payload.get("variable")},
            )
            logger.warning(
                "Incidencia ERROR_SENSOR para %s (%d fallos en ventana %ds)",
                device_key,
                counter,
                VENTANA_FALLOS_SENSOR,
            )
        except Exception as e:
            logger.error("No se pudo registrar incidencia ERROR_SENSOR: %s", e)

    async def _verificar_recuperacion(self, conn, device_key: str):
        pass

    def _limpiar_device(self, device_key: str):
        self._device_failures.pop(device_key, None)
        self._device_first_fail.pop(device_key, None)
        self._device_incidencia_logged.pop(device_key, None)
        self._device_dispositivo_id.pop(device_key, None)

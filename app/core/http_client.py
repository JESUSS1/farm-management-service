import asyncio
import json
import logging
from typing import Any

import aiohttp

from app.config import API_BASE_URL, API_KEY

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=15)


class HttpClient:
    def __init__(self):
        self._session: aiohttp.ClientSession | None = None
        self._headers: dict[str, str] = {
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
        }

    async def start(self):
        self._session = aiohttp.ClientSession(
            base_url=API_BASE_URL,
            headers=self._headers,
            timeout=TIMEOUT,
        )
        logger.info("HTTP client iniciado: %s", API_BASE_URL)

    async def stop(self):
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("HTTP client detenido")

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        if not self._session:
            raise RuntimeError("HTTPClient no iniciado")
        for attempt in range(3):
            try:
                async with self._session.request(method, path, **kwargs) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        logger.error("HTTP %d %s %s: %s", resp.status, method, path, text)
                        return None
                    if resp.status == 204:
                        return None
                    return await resp.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning("HTTP error (intento %d/3) %s %s: %s", attempt + 1, method, path, e)
                if attempt < 2:
                    await asyncio.sleep(1)
                else:
                    logger.error("HTTP error agotado %s %s: %s", method, path, e)
                    return None

    async def _get(self, path: str, params: dict | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, json_data: dict | None = None) -> Any:
        return await self._request("POST", path, json=json_data)

    async def _patch(self, path: str, json_data: dict | None = None) -> Any:
        return await self._request("PATCH", path, json=json_data)

    # Readings
    async def post_readings_batch(self, readings: list[dict]) -> int:
        result = await self._post("/service/readings/batch", {"readings": readings})
        return (result or {}).get("saved", 0)

    # Device lookup
    async def get_device_by_mac(self, mac: str) -> dict | None:
        result = await self._get(f"/service/devices/by-mac/{mac}")
        if result and result.get("found"):
            return result["device"]
        return None

    async def update_device_ip(self, dispositivo_id: int, ip: str):
        await self._patch(f"/service/devices/{dispositivo_id}/ip", {"ip": ip})

    async def get_device_registry(self) -> list[dict]:
        result = await self._get("/service/devices/registry")
        return result or []

    async def get_offline_devices(self, minutos: int = 5) -> list[dict]:
        result = await self._get("/service/devices/offline", {"minutos": minutos})
        return result or []

    async def get_recovered_devices(self, minutos: int = 5) -> list[dict]:
        result = await self._get("/service/devices/recovered", {"minutos": minutos})
        return result or []

    # Tasks
    async def get_pending_tasks(self, hora_str: str) -> list[dict]:
        result = await self._get("/service/tasks/pending", {"hora": hora_str})
        return result or []

    async def create_task_history(self, horario_tarea_dispositivo_id: int, estado: str = "INICIADA") -> int | None:
        result = await self._post("/service/task-history", {
            "horario_tarea_dispositivo_id": horario_tarea_dispositivo_id,
            "estado": estado,
        })
        return (result or {}).get("historial_tarea_id")

    async def finalize_task_history(self, horario_tarea_dispositivo_id: int, estado: str = "FINALIZADA"):
        await self._patch(f"/service/task-history/{horario_tarea_dispositivo_id}/finalize", {"estado": estado})

    async def update_schedule_last_execution(self, horario_tarea_id: int):
        await self._patch(f"/service/schedule/{horario_tarea_id}/last-execution")

    # Incidents
    async def create_incident(self, tipo: str, dispositivo_id: int | None, dispositivo_key: str, mensaje: str, detalle: dict | None = None):
        await self._post("/service/incidents", {
            "tipo": tipo,
            "dispositivo_id": dispositivo_id,
            "dispositivo_key": dispositivo_key,
            "mensaje": mensaje,
            "detalle": detalle,
        })

    async def resolve_incidents(self, dispositivo_key: str, tipo_error: str):
        await self._post("/service/incidents/resolve", {
            "dispositivo_key": dispositivo_key,
            "tipo_error": tipo_error,
        })

    async def check_pending_incident(self, dispositivo_key: str, tipo: str) -> bool:
        result = await self._get(f"/service/incidents/pending/{dispositivo_key}/{tipo}")
        return (result or {}).get("pending", False)

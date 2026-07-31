import logging
from typing import Optional

from app.config import DEVICE_PORTS

logger = logging.getLogger(__name__)

DEFAULT_COMMAND_PORT = 5000


class DeviceInfo:
    def __init__(self, row: dict):
        self.dispositivo_id: int = row["dispositivo_id"]
        self.device_key: str = row["device_key"]
        self.tipo_dispositivo_id: int = row["tipo_dispositivo_id"]
        self.tipo_nombre: str = row.get("tipo_nombre", "")
        self.ip_wifi: Optional[str] = row.get("ip_wifi")
        self.mac_wifi: Optional[str] = row.get("mac_wifi")
        self.mac_bluetooth: Optional[str] = row.get("mac_bluetooth")
        self.firmware_version: Optional[str] = row.get("firmware_version")
        self.dispositivo_padre_id: Optional[int] = row.get("dispositivo_padre_id")
        self.padre_ip: Optional[str] = row.get("padre_ip")

    @property
    def command_port(self) -> int:
        port = DEVICE_PORTS.get(self.tipo_nombre, DEFAULT_COMMAND_PORT)
        if self.tipo_nombre not in DEVICE_PORTS:
            logger.warning(
                "Tipo dispositivo '%s' no configurado en DEVICE_PORTS, "
                "usando puerto por defecto %d",
                self.tipo_nombre,
                DEFAULT_COMMAND_PORT,
            )
        return port

    @property
    def transport(self) -> str:
        if self.ip_wifi:
            return "wifi_tcp"
        return "rs485"


class DeviceRegistry:
    def __init__(self, http_client):
        self._http = http_client
        self._devices: dict[str, DeviceInfo] = {}

    async def refresh(self):
        try:
            rows = await self._http.get_device_registry()
            self._devices = {}
            for row in rows:
                info = DeviceInfo(row)
                self._devices[info.device_key] = info
            logger.info(
                "Registry refrescado: %d dispositivos cargados", len(self._devices)
            )
        except Exception as e:
            logger.error("Error refrescando registry: %s", e, exc_info=True)

    def get_by_key(self, device_key: str) -> Optional[DeviceInfo]:
        return self._devices.get(device_key)

    def get_all(self) -> list[DeviceInfo]:
        return list(self._devices.values())

    def get_by_ip(self, ip: str) -> Optional[DeviceInfo]:
        ip_clean = ip.split("/")[0]
        for d in self._devices.values():
            if d.ip_wifi and d.ip_wifi.split("/")[0] == ip_clean:
                return d
        return None

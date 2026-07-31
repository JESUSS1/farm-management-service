import logging

from app.core.http_client import HttpClient
from app.core.message import Message, MessageType
from app.handlers.base import Handler
from app.protocol.encoder import encode_command

logger = logging.getLogger(__name__)


class CommandHandler(Handler):
    def __init__(self, registry, tcp_client, http: HttpClient):
        self._registry = registry
        self._tcp_client = tcp_client
        self._http = http

    CENTRAL_CHILD_PORT = 5001

    async def handle(self, message: Message) -> bool:
        if message.type != MessageType.COMMAND:
            return False
        device_key = message.device_id
        accion = message.payload.get("accion")
        device = self._registry.get_by_key(device_key)
        if not device:
            logger.error("Dispositivo no encontrado: %s", device_key)
            return False

        has_parent = device.dispositivo_padre_id is not None and device.padre_ip is not None

        if has_parent:
            ip = device.padre_ip
            port = self.CENTRAL_CHILD_PORT
        else:
            if not device.ip_wifi:
                logger.error("Dispositivo %s sin IP WiFi", device_key)
                return False
            ip = device.ip_wifi
            port = device.command_port

        comando = encode_command(device_key, device.tipo_nombre, accion, has_parent=has_parent)
        if not comando:
            logger.error(
                "No se pudo codificar comando para %s: %s", device_key, accion
            )
            return False
        cmd_msg = Message(
            type=MessageType.COMMAND,
            device_id=device_key,
            payload={
                "ip": ip,
                "port": port,
                "comando": comando,
            },
        )
        logger.info(
            "[COMANDO] %s -> %s:%s (via padre: %s): %s",
            device_key, ip, port, has_parent, comando,
        )
        ok = await self._tcp_client.send(device_key, cmd_msg)
        await self._registrar_incidencia(device_key, device.dispositivo_id, accion, ok)
        return ok

    async def _registrar_incidencia(
        self, device_key: str, dispositivo_id: int, accion: str, ok: bool
    ):
        try:
            if ok:
                hay_pendiente = await self._http.check_pending_incident(
                    device_key, "ERROR_COMANDO"
                )
                if hay_pendiente:
                    await self._http.resolve_incidents(device_key, "ERROR_COMANDO")
                    await self._http.create_incident(
                        "RECUPERACION_COMANDO",
                        dispositivo_id,
                        device_key,
                        f"Comando {accion} enviado correctamente a {device_key} tras recuperacion",
                        {"accion": accion},
                    )
                    logger.info(
                        "Incidencia RECUPERACION_COMANDO para %s", device_key
                    )
            else:
                ya_existe = await self._http.check_pending_incident(
                    device_key, "ERROR_COMANDO"
                )
                if not ya_existe:
                    await self._http.create_incident(
                        "ERROR_COMANDO",
                        dispositivo_id,
                        device_key,
                        f"No se pudo enviar {accion} a {device_key}",
                        {"accion": accion},
                    )
                    logger.warning(
                        "Incidencia ERROR_COMANDO para %s (%s)",
                        device_key,
                        accion,
                    )
        except Exception as e:
            logger.error(
                "Error registrando incidencia para %s: %s",
                device_key,
                e,
                exc_info=True,
            )

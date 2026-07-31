import logging

from app.core.message import Message, MessageType

logger = logging.getLogger(__name__)


def decode_sensor_line(linea: str) -> Message | None:
    linea = linea.strip()
    datos = {}
    partes = linea.split(";")
    for parte in partes:
        if ":" in parte:
            clave, valor = parte.split(":", 1)
            datos[clave.strip().upper()] = valor.strip()

    if (
        "PARENT_DEVICE" in datos
        and "CHILD_DEVICE" in datos
        and "VARIABLE" in datos
        and "VALOR" in datos
    ):
        try:
            valor = float(datos["VALOR"])
        except ValueError:
            logger.warning("VALOR no numerico: %s", datos["VALOR"])
            return None

        return Message(
            type=MessageType.SENSOR_READING,
            device_id=datos["CHILD_DEVICE"],
            payload={
                "parent_device": datos["PARENT_DEVICE"],
                "variable": datos["VARIABLE"],
                "valor": valor,
                "unidad": datos.get("UNIDAD", ""),
                "firmware_version": datos.get("VERSION", ""),
            },
            raw=linea,
        )

    if "PARENT_DEVICE" in datos and "REGISTER_MAC" in datos:
        return Message(
            type=MessageType.REGISTRATION,
            device_id=datos["REGISTER_MAC"],
            payload={
                "mac": datos["REGISTER_MAC"],
                "parent_device": datos["PARENT_DEVICE"],
            },
            raw=linea,
        )

    if "DEVICE" in datos and "EVENTO" in datos:
        return Message(
            type=MessageType.EVENT,
            device_id=datos["DEVICE"],
            payload={"evento": datos["EVENTO"], "estado": datos.get("ESTADO", "")},
            raw=linea,
        )

    if "DEVICE" in datos and "ERROR" in datos:
        return Message(
            type=MessageType.ERROR,
            device_id=datos["DEVICE"],
            payload={"error": datos["ERROR"], "contexto": datos.get("SENSOR", "")},
            raw=linea,
        )

    if "DEVICE" in datos and "STATUS" in datos:
        return Message(
            type=MessageType.STATUS_RESPONSE,
            device_id=datos["DEVICE"],
            payload={"evento": "status", "status": datos.get("ESTADO", "")},
            raw=linea,
        )

    if "REGISTER_MAC" in datos:
        return Message(
            type=MessageType.REGISTRATION,
            device_id=datos["REGISTER_MAC"],
            payload={"mac": datos["REGISTER_MAC"]},
            raw=linea,
        )

    logger.debug("Linea no reconocida: %s", linea)
    return None

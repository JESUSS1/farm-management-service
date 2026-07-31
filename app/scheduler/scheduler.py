import asyncio
import logging

from datetime import datetime

from app.core.http_client import HttpClient

logger = logging.getLogger(__name__)

INTERVALO_SCHEDULER = 5
INTERVALO_REGISTRY_REFRESH = 60
TIMEOUT_OFFLINE = 5
INTERVALO_OFFLINE = 60


async def revisar_horarios(engine):
    http: HttpClient = engine.http
    ahora = datetime.now()
    hora_str = ahora.strftime("%H:%M")

    rows = await http.get_pending_tasks(hora_str)

    if not rows:
        return

    logger.info("Horarios pendientes a las %s: %d", hora_str, len(rows))

    for h in rows:
        horario_id = h["horario_tarea_id"]
        htd_id = h["horario_tarea_dispositivo_id"]
        device_key = h["device_key"]
        ip_wifi = h.get("ip_wifi")

        inicio_str = h["hora_inicio"][:5] if h.get("hora_inicio") else None
        fin_str = h["hora_fin"][:5] if h.get("hora_fin") else None

        if inicio_str == hora_str and h.get("accion_inicio_codigo"):
            if h.get("historial_tarea_id") is None:
                if ip_wifi:
                    ok = await engine.send_command(
                        device_key, h["accion_inicio_codigo"]
                    )
                    estado = "INICIADA" if ok else "ERROR_INICIO"
                else:
                    logger.warning("%s: sin IP WiFi, omitiendo", device_key)
                    estado = "ERROR_INICIO"
                await http.create_task_history(htd_id, estado)
                await http.update_schedule_last_execution(horario_id)
                logger.info(
                    "[INICIO] %s -> %s (%s)", device_key, h["accion_inicio_codigo"], estado
                )
            else:
                logger.debug("[SKIP] %s ya tiene historial activo", device_key)

        if fin_str == hora_str and h.get("accion_fin_codigo"):
            if (
                h.get("historial_tarea_id") is not None
                and h.get("historial_estado") == "INICIADA"
            ):
                if ip_wifi:
                    ok = await engine.send_command(
                        device_key, h["accion_fin_codigo"]
                    )
                    estado = "FINALIZADA" if ok else "ERROR_FINALIZACION"
                else:
                    logger.warning("%s: sin IP WiFi, omitiendo", device_key)
                    estado = "ERROR_FINALIZACION"
                await http.finalize_task_history(htd_id, estado)
                await http.update_schedule_last_execution(horario_id)
                logger.info(
                    "[FIN] %s -> %s (%s)", device_key, h["accion_fin_codigo"], estado
                )
            else:
                logger.debug(
                    "[SKIP FIN] %s no tiene inicio activo", device_key
                )


async def scheduler_loop(engine):
    logger.info("Scheduler iniciado (intervalo: %ds)", INTERVALO_SCHEDULER)
    while True:
        try:
            await revisar_horarios(engine)
        except Exception as e:
            logger.error("Error en scheduler: %s", e, exc_info=True)
        await asyncio.sleep(INTERVALO_SCHEDULER)


async def registry_refresh_loop(engine):
    logger.info(
        "Registry refresh loop iniciado (intervalo: %ds)", INTERVALO_REGISTRY_REFRESH
    )
    while True:
        await asyncio.sleep(INTERVALO_REGISTRY_REFRESH)
        try:
            await engine.refresh_registry()
        except Exception as e:
            logger.error("Error refrescando registry: %s", e, exc_info=True)


async def revisar_offline(engine):
    http: HttpClient = engine.http

    offlines = await http.get_offline_devices(TIMEOUT_OFFLINE)
    for d in offlines:
        await http.create_incident(
            "DEVICE_OFFLINE",
            d["dispositivo_id"],
            d["device_key"],
            f"Sin comunicación desde {d.get('ultima_comunicacion', '?')}",
        )
        logger.warning("OFFLINE: %s (%s)", d["device_key"], d.get("nombre"))

    recuperados = await http.get_recovered_devices(TIMEOUT_OFFLINE)
    for d in recuperados:
        await http.resolve_incidents(d["device_key"], "DEVICE_OFFLINE")
        await http.create_incident(
            "RECUPERACION_ONLINE",
            d["dispositivo_id"],
            d["device_key"],
            "Dispositivo volvió a comunicar",
        )
        logger.info("RECUPERADO: %s", d["device_key"])


async def offline_check_loop(engine):
    logger.info(
        "Offline check loop iniciado (intervalo: %ds, timeout: %dmin)",
        INTERVALO_OFFLINE,
        TIMEOUT_OFFLINE,
    )
    while True:
        await asyncio.sleep(INTERVALO_OFFLINE)
        try:
            await revisar_offline(engine)
        except Exception as e:
            logger.error("Error en offline check: %s", e, exc_info=True)

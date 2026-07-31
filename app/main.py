import asyncio
import logging
import signal

from app.config import LOG_LEVEL, RS485_ENABLED
from app.core.engine import Engine
from app.scheduler.scheduler import (
    offline_check_loop,
    registry_refresh_loop,
    scheduler_loop,
)
from app.version import __version__

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main_async():
    logger.info("farm-management-service v%s", __version__)
    modo = "RS485 + WiFi" if RS485_ENABLED else "WiFi-only (test)"
    logger.info("Modo: %s", modo)

    engine = Engine()
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Señal de parada recibida, cerrando...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    await engine.start()

    scheduler_task = asyncio.create_task(_scheduler_with_restart(engine))
    registry_task = asyncio.create_task(registry_refresh_loop(engine))
    offline_task = asyncio.create_task(offline_check_loop(engine))

    await _wait_for_stop(stop_event)

    scheduler_task.cancel()
    registry_task.cancel()
    offline_task.cancel()
    await asyncio.gather(
        scheduler_task, registry_task, offline_task, return_exceptions=True
    )

    try:
        await asyncio.wait_for(engine.stop(), timeout=10)
    except asyncio.TimeoutError:
        logger.warning("Shutdown timeout forzado")
    logger.info("Servicio detenido")


async def _scheduler_with_restart(engine):
    while True:
        try:
            await scheduler_loop(engine)
        except Exception as e:
            logger.error(
                "Scheduler crashed, reiniciando en 5s: %s", e, exc_info=True
            )
            await asyncio.sleep(5)


async def _wait_for_stop(stop_event: asyncio.Event):
    await stop_event.wait()
    logger.info("Deteniendo tareas...")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

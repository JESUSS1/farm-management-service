import time
from serial.serialutil import SerialException

from app.config import RS485_ENABLED
from app.database.db import get_connection
from app.database.repository import save_sensor_reading
from app.serial_port.rs485_reader import open_rs485
from app.serial_port.parser import parse_sensor_data
from app.scheduler.scheduler import revisar_horarios
from app.version import __version__

print(__version__)
INTERVALO_SCHEDULER = 5


def main():
    conn = get_connection()

    if RS485_ENABLED:
        ser = open_rs485()
        modo = "RS485 + WiFi"
    else:
        ser = None
        modo = "WiFi-only (test)"

    print(f"Sistema iniciado — modo: {modo}")
    ultimo_scheduler = 0
    time.sleep(2)

    try:
        while True:
            ahora = time.time()

            if ahora - ultimo_scheduler >= INTERVALO_SCHEDULER:
                revisar_horarios(conn)
                ultimo_scheduler = ahora

            if ser is not None:
                try:
                    linea = ser.readline().decode(errors="ignore").strip()
                except SerialException as e:
                    print("Error serial:", e)
                    print("Posible desconexión del RS485/ESP32")
                    break

                if not linea:
                    time.sleep(0.2)
                    continue

                print("Dato recibido:", linea)
                lectura = parse_sensor_data(linea)

                if lectura is None:
                    print("Dato ignorado")
                    continue

                save_sensor_reading(conn, lectura)
                print("Guardado en DB")
            else:
                time.sleep(INTERVALO_SCHEDULER)

    except KeyboardInterrupt:
        print("\nPrograma detenido")

    finally:
        if ser is not None:
            ser.close()
        conn.close()
        print("Puerto y base de datos cerrados")


if __name__ == "__main__":
    main()

import time
from serial import SerialException

from app.database.db import get_connection
from app.database.repository import save_sensor_reading
from app.serial.rs485_reader import open_rs485
from app.serial.parser import parse_sensor_data
from app.scheduler.scheduler import revisar_horarios
from app.version import __version__
from app.command_dispatcher import enviar_comando

print(__version__)
INTERVALO_SCHEDULER = 5  # segundos


def enviar_comando_rs485(ser, comando):
    ser.write((comando + "\n").encode())
    ser.flush()
    print(f"Comando enviado: {comando}")


def main():
    conn = get_connection()
    ser = open_rs485()

    ultimo_scheduler = 0

    print("Sistema iniciado")
    print("Escuchando RS485 y guardando en PostgreSQL...")

    time.sleep(2)

    try:
        while True:
            try:
                ahora = time.time()

                if ahora - ultimo_scheduler >= INTERVALO_SCHEDULER:
                    revisar_horarios(conn, enviar_comando)
                    ultimo_scheduler = ahora

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

    except KeyboardInterrupt:
        print("\nPrograma detenido")

    finally:
        ser.close()
        conn.close()
        print("Puerto y base de datos cerrados")


if __name__ == "__main__":
    main()
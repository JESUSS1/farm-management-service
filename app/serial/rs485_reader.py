import serial
from app.config import RS485_PORT, RS485_BAUDRATE

def open_rs485():
    return serial.Serial(
        port=RS485_PORT,
        baudrate=RS485_BAUDRATE,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=1,
    )
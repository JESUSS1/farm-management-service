import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}

RS485_PORT = os.getenv("RS485_PORT", "/dev/ttyUSB0")
RS485_BAUDRATE = int(os.getenv("RS485_BAUDRATE", "9600"))
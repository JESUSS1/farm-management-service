import os
from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")

RS485_PORT = os.getenv("RS485_PORT", "/dev/ttyUSB0")
RS485_BAUDRATE = int(os.getenv("RS485_BAUDRATE", "9600"))
RS485_ENABLED = os.getenv("RS485_ENABLED", "true").lower() == "true"

WIFI_SERVER_HOST = os.getenv("WIFI_SERVER_HOST", "0.0.0.0")
WIFI_SERVER_PORT = int(os.getenv("WIFI_SERVER_PORT", "5000"))

DEVICE_PORTS = {
    "ESP32_SENSOR": int(os.getenv("ESP32_SENSOR_PORT", "5001")),
    "ESP32_FEEDER": int(os.getenv("ESP32_FEEDER_PORT", "5002")),
}

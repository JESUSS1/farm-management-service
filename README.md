# farm-management-service

Puente asíncrono entre dispositivos ESP32 y PostgreSQL. Recibe datos de sensores, ejecuta tareas programadas y envía comandos a actuadores.

## Requisitos

- Python 3.11+
- PostgreSQL 13+
- Acceso de red a los dispositivos ESP32

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env-example .env
# editar .env con credenciales y configuración
```

## Configuración

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DB_NAME` | — | Base de datos |
| `DB_USER` | — | Usuario BD |
| `DB_PASSWORD` | — | Contraseña BD |
| `DB_HOST` | `localhost` | Host BD |
| `DB_PORT` | `5432` | Puerto BD |
| `RS485_ENABLED` | `false` | Habilitar RS485 (Fase 2) |
| `WIFI_SERVER_HOST` | `0.0.0.0` | Interfaz TCP server |
| `WIFI_SERVER_PORT` | `5000` | Puerto para recibir datos de sensores |
| `ESP32_SENSOR_PORT` | `5001` | Puerto de comandos para sensores |
| `ESP32_FEEDER_PORT` | `5002` | Puerto de comandos para feeders |
| `LOG_LEVEL` | `INFO` | Nivel de logging (DEBUG, INFO, WARNING, ERROR) |

## Ejecución

```bash
source .venv/bin/activate
python -m app.main
```

## Arquitectura

```
                    ┌─────────────────────────────────────┐
                    │            Engine                    │
                    │  ┌──────────┐  ┌──────────────────┐ │
                    │  │ Registry │  │  SensorHandler   │ │
                    │  │  (cache) │  │  (buffer+flush)  │ │
                    │  └────┬─────┘  └────────┬─────────┘ │
                    │       │                 │           │
                    │  ┌────▼─────────────────▼──────────┐│
                    │  │     CommandHandler              ││
                    │  └───────────────┬─────────────────┘│
                    └──────────────────┼──────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
         TCP Server (5000)        TCP Client              Scheduler (5s)
        (recibe datos sensores)  (envía comandos)     (poll horario_tarea)
              │                        │                        │
              ▼                        ▼                        │
         [ESP32 sensores]      [ESP32 feeder] ◄────────────────┘
```

## Puertos

| Componente | Puerto | Dirección |
|------------|--------|-----------|
| Service (recepción datos) | 5000 | ← Dispositivos |
| Sensor ESP32 (comandos) | 5001 | → Service envía |
| Feeder ESP32 (comandos) | 5002 | → Service envía |

## Protocolo

### Recepción (dispositivo → service)

Formato `CLAVE:VALOR;`:

```
DEVICE:esp32_A1_01;SENSOR:hc_sr04_1;VARIABLE:distancia;VALOR:15.32;UNIDAD:cm;VERSION:0.2.0
DEVICE:esp32_A1_01;EVENTO:servo;ESTADO:abierto
DEVICE:esp32_A1_01;STATUS:servo;ESTADO:abierto
DEVICE:esp32_A1_01;SENSOR:hc_sr04_1;VARIABLE:distancia;ERROR:sin_respuesta
```

### Envío (service → dispositivo)

- **Feeder**: `LED_ON\n` o `LED_OFF\n`
- **Sensor**: `TARGET:esp32_A1_01;ORDEN:ABRIR\n`

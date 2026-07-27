def save_sensor_reading(conn, lectura):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO lecturas_sensor
            (device_id, sensor, variable, valor, unidad, firmware_version, dato_original)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                lectura["device_id"],
                lectura["sensor"],
                lectura["variable"],
                lectura["valor"],
                lectura["unidad"],
                lectura["firmware_version"],
                lectura["dato_original"],
            ),
        )

    conn.commit()


def crear_historial_inicio(conn, horario_tarea_dispositivo_id, estado="INICIADA"):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO historial_tarea
                (horario_tarea_dispositivo_id, fecha_inicio, estado)
            VALUES (%s, NOW(), %s)
            RETURNING historial_tarea_id
            """,
            (horario_tarea_dispositivo_id, estado),
        )
        return cursor.fetchone()["historial_tarea_id"]


def finalizar_historial(conn, horario_tarea_dispositivo_id, estado="FINALIZADA"):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE historial_tarea
            SET fecha_finalizacion = NOW(),
                estado = %s
            WHERE horario_tarea_dispositivo_id = %s
              AND estado = 'INICIADA'
              AND fecha_finalizacion IS NULL
            """,
            (estado, horario_tarea_dispositivo_id),
        )

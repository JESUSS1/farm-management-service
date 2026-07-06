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
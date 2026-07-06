from datetime import datetime


def revisar_horarios(conn, enviar_comando_rs485):
    ahora = datetime.now()
    hora_actual = ahora.strftime("%H:%M")
    fecha_actual = ahora.date()

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, nombre, target, funcion
            FROM horario_funciones
            WHERE activo = TRUE
              AND TO_CHAR(hora, 'HH24:MI') = %s
              AND (ultima_ejecucion IS NULL OR ultima_ejecucion <> %s)
            """,
            (hora_actual, fecha_actual),
        )

        horarios = cursor.fetchall()

        for horario in horarios:
            id_horario, nombre, target, funcion = horario

            comando = f"TARGET:{target};ORDEN:{funcion}"
            enviar_comando_rs485(comando)

            cursor.execute(
                """
                UPDATE horario_funciones
                SET ultima_ejecucion = %s
                WHERE id = %s
                """,
                (fecha_actual, id_horario),
            )

            print(f"Ejecutado: {nombre} -> {comando}")

    conn.commit()
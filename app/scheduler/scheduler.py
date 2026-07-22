from datetime import datetime

# Traducción entre funciones de la BD y comandos reales
COMANDOS = {
    "ENCENDER_LED": "LED_ON",
    "APAGAR_LED": "LED_OFF",
    "OPEN": "OPEN",
    "CLOSE": "CLOSE",
    "STATUS": "STATUS",
}


def revisar_horarios(conn, enviar_comando):
    ahora = datetime.now()
    hora_actual = ahora.strftime("%H:%M")
    fecha_actual = ahora.date()
    print("Hora actual:", hora_actual)
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
        print("Horarios encontrados:", len(horarios))
        for horario in horarios:
            id_horario = horario["id"]
            nombre = horario["nombre"]
            target = horario["target"]
            funcion = horario["funcion"]

            comando = COMANDOS.get(funcion.upper())

            print("Horario:", nombre, target, funcion)
            print("Comando traducido:", comando)

            if comando is None:
                print(f"Función desconocida: {funcion}")
                continue

            enviar_comando(target, comando)
            print(f"Target: {target}")
            print(f"Función BD: {funcion}")
            print(f"Comando: {comando}")

            cursor.execute(
                """
                UPDATE horario_funciones
                SET ultima_ejecucion = %s
                WHERE id = %s
                """,
                (fecha_actual, id_horario),
            )

            print(f"Ejecutado: {nombre} -> {target} : {comando}")

    conn.commit()
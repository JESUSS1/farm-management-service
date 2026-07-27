from datetime import datetime

from app.command_dispatcher import enviar_comando_wifi_por_ip, PUERTO_COMANDO
from app.database.repository import (
    crear_historial_inicio,
    finalizar_historial,
)

ACCION_TO_COMANDO = {
    "TURN_ON": "LED_ON",
    "TURN_OFF": "LED_OFF",
}


def revisar_horarios(conn):
    ahora = datetime.now()
    hora_str = ahora.strftime("%H:%M")

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ht.horario_tarea_id,
                ht.hora_inicio::TEXT,
                ht.hora_fin::TEXT,
                ai.codigo AS accion_inicio_codigo,
                af.codigo AS accion_fin_codigo,
                htd.horario_tarea_dispositivo_id,
                d.dispositivo_id,
                d.device_key,
                d.ip_wifi::TEXT,
                hist.historial_tarea_id,
                hist.estado AS historial_estado
            FROM horario_tarea ht
            JOIN tarea t ON t.tarea_id = ht.tarea_id
                AND t.estado = TRUE AND t.eliminado_at IS NULL
            JOIN accion ai ON ai.accion_id = t.accion_inicio_id
            LEFT JOIN accion af ON af.accion_id = t.accion_fin_id
            JOIN horario_tarea_dispositivo htd ON htd.horario_tarea_id = ht.horario_tarea_id
                AND htd.estado = TRUE AND htd.eliminado_at IS NULL
            JOIN dispositivo d ON d.dispositivo_id = htd.dispositivo_id
                AND d.estado = TRUE AND d.eliminado_at IS NULL
            LEFT JOIN historial_tarea hist ON hist.horario_tarea_dispositivo_id = htd.horario_tarea_dispositivo_id
                AND hist.estado = 'INICIADA' AND hist.eliminado_at IS NULL
            WHERE ht.estado = TRUE AND ht.eliminado_at IS NULL
              AND EXTRACT(ISODOW FROM CURRENT_TIMESTAMP) = ANY(ht.dias_semana)
              AND (
                  (TO_CHAR(ht.hora_inicio, 'HH24:MI') = %s)
                  OR (ht.hora_fin IS NOT NULL AND TO_CHAR(ht.hora_fin, 'HH24:MI') = %s)
              )
            """,
            (hora_str, hora_str),
        )

        horarios = cursor.fetchall()

    if not horarios:
        return

    print(f"Horarios pendientes a las {hora_str}: {len(horarios)}")

    with conn.cursor() as cursor:
        for h in horarios:
            horario_id = h["horario_tarea_id"]
            htd_id = h["horario_tarea_dispositivo_id"]
            device_key = h["device_key"]
            ip_wifi = h["ip_wifi"]

            inicio_str = h["hora_inicio"][:5] if h["hora_inicio"] else None
            fin_str = h["hora_fin"][:5] if h["hora_fin"] else None

            # --- ACCIÓN DE INICIO ---
            if inicio_str == hora_str and h["accion_inicio_codigo"]:
                if h["historial_tarea_id"] is None:
                    comando = ACCION_TO_COMANDO.get(h["accion_inicio_codigo"])
                    if not comando:
                        print(f"  Acción inicio desconocida: {h['accion_inicio_codigo']}")
                        continue

                    if ip_wifi:
                        ip_limpia = ip_wifi.split("/")[0]
                        ok = enviar_comando_wifi_por_ip(ip_limpia, PUERTO_COMANDO, comando)
                        estado = "INICIADA" if ok else "ERROR_INICIO"
                    else:
                        print(f"  {device_key}: sin IP WiFi, omitiendo")
                        estado = "ERROR_INICIO"

                    crear_historial_inicio(conn, htd_id, estado)
                    _actualizar_ultima_ejecucion(cursor, horario_id)
                    print(f"  [INICIO] {device_key} -> {comando} ({estado})")
                else:
                    print(f"  [SKIP] {device_key} ya tiene historial activo")

            # --- ACCIÓN DE FIN ---
            if fin_str == hora_str and h["accion_fin_codigo"]:
                if h["historial_tarea_id"] is not None and h["historial_estado"] == "INICIADA":
                    comando = ACCION_TO_COMANDO.get(h["accion_fin_codigo"])
                    if not comando:
                        print(f"  Acción fin desconocida: {h['accion_fin_codigo']}")
                        continue

                    if ip_wifi:
                        ip_limpia = ip_wifi.split("/")[0]
                        ok = enviar_comando_wifi_por_ip(ip_limpia, PUERTO_COMANDO, comando)
                        estado = "FINALIZADA" if ok else "ERROR_FINALIZACION"
                    else:
                        print(f"  {device_key}: sin IP WiFi, omitiendo")
                        estado = "ERROR_FINALIZACION"

                    finalizar_historial(conn, htd_id, estado)
                    _actualizar_ultima_ejecucion(cursor, horario_id)
                    print(f"  [FIN] {device_key} -> {comando} ({estado})")
                else:
                    print(f"  [SKIP FIN] {device_key} no tiene inicio activo")

        conn.commit()


def _actualizar_ultima_ejecucion(cursor, horario_tarea_id):
    cursor.execute(
        """
        UPDATE horario_tarea
        SET ultima_ejecucion = NOW()
        WHERE horario_tarea_id = %s
        """,
        (horario_tarea_id,),
    )

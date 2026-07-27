def parse_sensor_data(linea: str):
    print(f"RAW: {linea}")
    linea = linea.strip()

    datos = {}
    partes = linea.split(";")

    for parte in partes:
        if ":" in parte:
            clave, valor = parte.split(":", 1)
            datos[clave.strip().upper()] = valor.strip()

    if "DEVICE" in datos and "SENSOR" in datos and "VARIABLE" in datos and "VALOR" in datos:
        return {
            "device_id": datos["DEVICE"],
            "sensor": datos["SENSOR"],
            "variable": datos["VARIABLE"],
            "valor": float(datos["VALOR"]),
            "unidad": datos.get("UNIDAD", ""),
            "firmware_version": datos.get("VERSION", ""),
            "dato_original": linea,
        }

    return None
def encode_command(device_key: str, tipo_nombre: str, accion_codigo: str, has_parent: bool = False) -> str:
    if has_parent:
        return f"TARGET:{device_key};ORDEN:{accion_codigo};"
    return accion_codigo

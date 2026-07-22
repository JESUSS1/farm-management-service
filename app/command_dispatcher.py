import socket


def enviar_comando_rs485(target, comando):
    # De momento solo mostramos el mensaje.
    # Luego aquí irá el envío real por RS485.
    mensaje = f"TARGET:{target};ORDEN:{comando}"
    print(f"[RS485] {mensaje}")


def enviar_comando_wifi(target, comando):
    dispositivos = {
        "esp32_2": ("192.168.0.112", 5000),  # Cambia la IP por la de tu ESP32
    }

    if target not in dispositivos:
        print(f"Dispositivo WiFi no registrado: {target}")
        return

    ip, puerto = dispositivos[target]

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((ip, puerto))
            s.sendall((comando + "\n").encode())

        print(f"[WiFi] {target} <- {comando}")

    except Exception as e:
        print(f"Error enviando comando a {target}: {e}")


def enviar_comando(target, comando):
    """
    Decide automáticamente por qué medio enviar el comando.
    """
    print(f"Dispatcher -> target={target}, comando={comando}")
    # Dispositivos WiFi
    if target == "esp32_2":
        enviar_comando_wifi(target, comando)

    # Todos los demás por RS485
    else:
        enviar_comando_rs485(target, comando)
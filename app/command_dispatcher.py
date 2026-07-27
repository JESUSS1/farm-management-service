import socket


PUERTO_COMANDO = 5000


def enviar_comando_wifi_por_ip(ip, puerto, comando):
    try:
        ip = ip.split("/")[0]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((ip, puerto))
            s.sendall((comando + "\n").encode())
        print(f"[WiFi] {ip}:{puerto} <- {comando}")
        return True
    except Exception as e:
        print(f"[WiFi] Error enviando a {ip}:{puerto}: {e}")
        return False


def enviar_comando_por_ip(ip, comando, puerto=PUERTO_COMANDO):
    return enviar_comando_wifi_por_ip(ip, puerto, comando)


def enviar_comando_rs485(target, comando):
    mensaje = f"TARGET:{target};ORDEN:{comando}"
    print(f"[RS485] {mensaje}")


def enviar_comando_wifi(target, comando):
    dispositivos = {
        "esp32_2": ("192.168.0.112", 5000),
    }

    if target not in dispositivos:
        print(f"Dispositivo WiFi no registrado: {target}")
        return

    ip, puerto = dispositivos[target]
    enviar_comando_wifi_por_ip(ip, puerto, comando)


def enviar_comando(target, comando):
    print(f"Dispatcher -> target={target}, comando={comando}")
    if target == "esp32_2":
        enviar_comando_wifi(target, comando)
    else:
        enviar_comando_rs485(target, comando)

import socket
import threading
import json
import hashlib

HOST = "127.0.0.1"
PORT = 5000

tareas = [
    {"id_tarea": 1, "inicio": "aaa", "fin": "azz", "longitud": 3},
    {"id_tarea": 2, "inicio": "baa", "fin": "bzz", "longitud": 3},
]

hash_objetivo = hashlib.sha256("abc".encode("utf-8")).hexdigest()
candado_tareas = threading.Lock()


# ===================== FUNCIONES DE UTILIDAD =====================

def enviar_json(conexion, datos):
    mensaje = json.dumps(datos).encode("utf-8")
    conexion.sendall(mensaje + b"\n")


def recibir_json(conexion):
    datos = conexion.recv(4096)
    if not datos:
        return None
    try:
        texto = datos.decode("utf-8").strip()
        return json.loads(texto)
    except:
        return None


# ===================== MANEJO DE CLIENTES =====================

def atender_cliente(conexion, direccion):

    print(f"[SERVIDOR] Cliente conectado: {direccion}")

    mensaje_inicial = recibir_json(conexion)
    print(f"[SERVIDOR] Mensaje inicial recibido: {mensaje_inicial}")

    # Buscar una tarea que asignar
    with candado_tareas:
        if tareas:
            tarea = tareas.pop(0)
            mensaje_tarea = {
                "tipo": "tarea",
                "id_tarea": tarea["id_tarea"],
                "inicio": tarea["inicio"],
                "fin": tarea["fin"],
                "longitud": tarea["longitud"],
                "hash": hash_objetivo
            }
            enviar_json(conexion, mensaje_tarea)
        else:
            enviar_json(conexion, {"tipo": "sin_tarea"})
            conexion.close()
            return

    # Esperar respuesta del cliente
    while True:
        mensaje = recibir_json(conexion)
        if mensaje is None:
            print(f"[SERVIDOR] Cliente desconectado: {direccion}")
            break

        print(f"[SERVIDOR] Respuesta de {direccion}: {mensaje}")

        if mensaje.get("tipo") == "encontrado":
            print(f"[SERVIDOR] ¡Contraseña encontrada!: {mensaje['password']}")
            break

        elif mensaje.get("tipo") == "terminado":
            print(f"[SERVIDOR] Cliente terminó la tarea {mensaje.get('id_tarea')}")
            break

    conexion.close()


# ===================== FUNCIÓN PRINCIPAL =====================

def main():
    print("[SERVIDOR] Iniciando servidor...")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind((HOST, PORT))
        servidor.listen()
        print(f"[SERVIDOR] Escuchando en {HOST}:{PORT}")

        while True:
            conexion, direccion = servidor.accept()
            hilo = threading.Thread(target=atender_cliente, args=(conexion, direccion), daemon=True)
            hilo.start()


if __name__ == "__main__":
    main()

import socket
import json
import threading
import time
import itertools
import hashlib
import string

HOST = "127.0.0.1"
PORT = 5000

contraseña_encontrada = threading.Event()



def enviar_json(socket_cliente, datos):
    mensaje = json.dumps(datos).encode("utf-8")
    socket_cliente.sendall(mensaje + b"\n")


def recibir_json(socket_cliente):
    datos = socket_cliente.recv(4096)
    if not datos:
        return None
    try:
        texto = datos.decode("utf-8").strip()
        return json.loads(texto)
    except:
        return None


def calcular_hash_sha256(cadena):
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest()



def hilo_trabajo(info_tarea, id_hilo, total_hilos, socket_cliente):
    id_tarea = info_tarea["id_tarea"]
    inicio = info_tarea["inicio"]
    fin = info_tarea["fin"]
    longitud = info_tarea["longitud"]
    hash_objetivo = info_tarea["hash"]

    caracteres = string.ascii_lowercase  

    print(f"[CLIENTE] Hilo {id_hilo} trabajando en tarea {id_tarea}...")

    contador_global = 0

    for tupla_letras in itertools.product(caracteres, repeat=longitud):
        if contraseña_encontrada.is_set():
            return

        candidato = "".join(tupla_letras)

        if not (inicio <= candidato <= fin):
            continue

        if (contador_global % total_hilos) != id_hilo:
            contador_global += 1
            continue

        contador_global += 1

        hash_candidato = calcular_hash_sha256(candidato)

        if hash_candidato == hash_objetivo:
            print(f"[CLIENTE] ¡Hilo {id_hilo} encontró la contraseña!: {candidato}")
            contraseña_encontrada.set()

            enviar_json(socket_cliente, {
                "tipo": "encontrado",
                "id_tarea": id_tarea,
                "password": candidato
            })
            return

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
        cliente.connect((HOST, PORT))
        print("[CLIENTE] Conectado al servidor.")

        enviar_json(cliente, {"tipo": "hola", "cliente_id": "cliente_demo"})

        mensaje = recibir_json(cliente)
        print(f"[CLIENTE] Mensaje del servidor: {mensaje}")

        if mensaje is None or mensaje.get("tipo") == "sin_tarea":
            print("[CLIENTE] No hay tarea disponible. Cerrando.")
            return

        if mensaje.get("tipo") == "tarea":
            tarea = mensaje
            hilos = []
            NUM_HILOS = 4

            contraseña_encontrada.clear()

            for i in range(NUM_HILOS):
                t = threading.Thread(
                    target=hilo_trabajo,
                    args=(tarea, i, NUM_HILOS, cliente),
                    daemon=True
                )
                hilos.append(t)
                t.start()

            for t in hilos:
                t.join()

            if not contraseña_encontrada.is_set():
                enviar_json(cliente, {
                    "tipo": "terminado",
                    "id_tarea": tarea["id_tarea"]
                })
                print("[CLIENTE] Tarea completada, contraseña no encontrada en este rango.")


if __name__ == "__main__":
    main()

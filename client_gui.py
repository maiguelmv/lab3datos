# client_gui.py
import socket
import json
import threading
import itertools
import hashlib
import string
import time
import tkinter as tk
from tkinter import ttk, messagebox

# ===================== CONFIGURACIÓN DE RED =====================

HOST = "127.0.0.1"
PORT = 5000

contraseña_encontrada = threading.Event()
intentos_realizados = 0
candado_intentos = threading.Lock()
candado_envio = threading.Lock()


# ===================== UTILIDADES JSON / HASH =====================

def enviar_json(socket_cliente, datos):
    mensaje = json.dumps(datos).encode("utf-8")
    with candado_envio:
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


# ===================== TRABAJO DE FUERZA BRUTA =====================

def hilo_trabajo(info_tarea, id_hilo, total_hilos, socket_cliente,
                 callback_estado, callback_contraseña_gui):
    global intentos_realizados

    id_tarea = info_tarea["id_tarea"]
    inicio = info_tarea["inicio"]
    fin = info_tarea["fin"]
    longitud = info_tarea["longitud"]
    hash_objetivo = info_tarea["hash"]

    caracteres = string.ascii_lowercase
    callback_estado(f"Hilo {id_hilo} trabajando...")

    indice_global = 0

    for tupla_letras in itertools.product(caracteres, repeat=longitud):
        if contraseña_encontrada.is_set():
            return

        candidato = "".join(tupla_letras)

        if not (inicio <= candidato <= fin):
            continue

        if (indice_global % total_hilos) != id_hilo:
            indice_global += 1
            continue
        indice_global += 1

        with candado_intentos:
            intentos_realizados += 1

        if calcular_hash_sha256(candidato) == hash_objetivo:
            contraseña_encontrada.set()
            callback_estado(f"Hilo {id_hilo} encontró la contraseña")
            callback_contraseña_gui(candidato)

            enviar_json(socket_cliente, {
                "tipo": "encontrado",
                "id_tarea": id_tarea,
                "password": candidato
            })
            return


# ===================== LÓGICA PRINCIPAL DEL CLIENTE =====================

def hilo_cliente_principal(root, vars_gui, boton_conectar):
    global intentos_realizados
    intentos_realizados = 0
    contraseña_encontrada.clear()

    estado, hash_txt, rango_txt, intentos_txt, contra_txt, tiempo_txt, vel_txt = vars_gui

    root.after(0, lambda: boton_conectar.config(state="disabled"))
    inicio = time.time()

    def set_estado(msg):
        root.after(0, lambda: estado.set(msg))

    def set_contra(valor):
        root.after(0, lambda: contra_txt.set(f"Contraseña encontrada: {valor}"))

    def actualizar_metricas():
        elapsed = time.time() - inicio
        root.after(0, lambda: intentos_txt.set(f"Intentos: {intentos_realizados}"))
        root.after(0, lambda: tiempo_txt.set(f"Tiempo: {elapsed:.1f} s"))
        if elapsed > 0:
            vel = int(intentos_realizados / elapsed)
            root.after(0, lambda: vel_txt.set(f"Velocidad: {vel} intentos/s"))
        else:
            root.after(0, lambda: vel_txt.set("Velocidad: -"))

    try:
        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.connect((HOST, PORT))
        set_estado("Conectado al servidor")

        enviar_json(cliente, {"tipo": "hola", "cliente_id": "cliente_gui"})
        mensaje = recibir_json(cliente)
        print("[CLIENTE-GUI] Mensaje del servidor:", mensaje)

        if mensaje is None or mensaje.get("tipo") == "sin_tarea":
            set_estado("No hay tarea disponible")
            cliente.close()
            return

        if mensaje.get("tipo") == "tarea":
            tarea = mensaje
            root.after(0, lambda: hash_txt.set(f"Hash objetivo: {tarea['hash']}"))
            root.after(0, lambda: rango_txt.set(
                f"Rango: {tarea['inicio']}  →  {tarea['fin']} (len {tarea['longitud']})"
            ))
            set_estado("Iniciando fuerza bruta...")

            hilos = []
            NUM_HILOS = 4
            for i in range(NUM_HILOS):
                t = threading.Thread(
                    target=hilo_trabajo,
                    args=(tarea, i, NUM_HILOS, cliente,
                          set_estado, set_contra),
                    daemon=True
                )
                hilos.append(t)
                t.start()

            trabajando = True
            while trabajando:
                trabajando = any(t.is_alive() for t in hilos)
                actualizar_metricas()
                if contraseña_encontrada.is_set():
                    break
                time.sleep(0.3)

            for t in hilos:
                t.join()

            if not contraseña_encontrada.is_set():
                enviar_json(cliente, {
                    "tipo": "terminado",
                    "id_tarea": tarea["id_tarea"]
                })
                set_estado("Fin del rango: contraseña no encontrada")

        cliente.close()

    except ConnectionRefusedError:
        root.after(0, lambda: messagebox.showerror(
            "Error de conexión", "No se pudo conectar al servidor. ¿Está encendido?"
        ))
        root.after(0, lambda: estado.set("Error: servidor no disponible"))
    except Exception as e:
        root.after(0, lambda: messagebox.showerror(
            "Error", f"Ocurrió un error en el cliente:\n{e}"
        ))
        root.after(0, lambda: estado.set("Error en la ejecución"))
    finally:
        root.after(0, lambda: boton_conectar.config(state="normal"))


# ===================== INTERFAZ GRÁFICA =====================

def crear_interfaz_cliente():
    root = tk.Tk()
    root.title("Cliente Fuerza Bruta Distribuida")
    root.geometry("780x460")
    root.configure(bg="#020617")  # fondo oscuro

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except:
        pass

    # Tarjeta principal centrada con padding, usando pack (no place)
    card = tk.Frame(root, bg="#0f172a", bd=1, relief="ridge")
    card.pack(expand=True, fill="both", padx=30, pady=30)

    # Título
    titulo = tk.Label(
        card,
        text="Cliente de Fuerza Bruta Distribuida",
        bg="#0f172a",
        fg="#e5e7eb",
        font=("Segoe UI", 16, "bold")
    )
    titulo.pack(pady=(10, 8))

    # Variables de texto
    texto_estado = tk.StringVar(value="Esperando para conectar...")
    texto_hash = tk.StringVar(value="Hash objetivo: -")
    texto_rango = tk.StringVar(value="Rango: -")
    texto_intentos = tk.StringVar(value="Intentos: 0")
    texto_contraseña = tk.StringVar(value="Contraseña encontrada: -")
    texto_tiempo = tk.StringVar(value="Tiempo: 0.0 s")
    texto_velocidad = tk.StringVar(value="Velocidad: -")

    # Panel de información
    panel_info = tk.Frame(card, bg="#111827")
    panel_info.pack(fill="x", padx=20, pady=(0, 8))

    lbl_info = tk.Label(panel_info, text="Información de búsqueda",
                        bg="#111827", fg="#93c5fd",
                        font=("Segoe UI", 10, "bold"))
    lbl_info.pack(anchor="w", pady=(6, 2))

    lbl_estado = tk.Label(panel_info, textvariable=texto_estado,
                          bg="#111827", fg="#e5e7eb", anchor="w",
                          justify="left", wraplength=700)
    lbl_estado.pack(anchor="w")

    lbl_hash = tk.Label(panel_info, textvariable=texto_hash,
                        bg="#111827", fg="#9ca3af", anchor="w",
                        font=("Consolas", 9), wraplength=700)
    lbl_hash.pack(anchor="w", pady=(2, 0))

    lbl_rango = tk.Label(panel_info, textvariable=texto_rango,
                         bg="#111827", fg="#d1d5db", anchor="w")
    lbl_rango.pack(anchor="w", pady=(2, 6))

    # Panel de métricas
    panel_metricas = tk.Frame(card, bg="#020617")
    panel_metricas.pack(fill="x", padx=20, pady=(0, 8))

    box_metricas = tk.Frame(panel_metricas, bg="#111827")
    box_metricas.pack(fill="x")

    lbl_m_title = tk.Label(box_metricas, text="Métricas de ejecución",
                           bg="#111827", fg="#93c5fd",
                           font=("Segoe UI", 10, "bold"))
    lbl_m_title.pack(anchor="w", pady=(6, 2))

    lbl_intentos = tk.Label(box_metricas, textvariable=texto_intentos,
                            bg="#111827", fg="#e5e7eb")
    lbl_intentos.pack(anchor="w")

    lbl_tiempo = tk.Label(box_metricas, textvariable=texto_tiempo,
                          bg="#111827", fg="#e5e7eb")
    lbl_tiempo.pack(anchor="w")

    lbl_velocidad = tk.Label(box_metricas, textvariable=texto_velocidad,
                             bg="#111827", fg="#e5e7eb")
    lbl_velocidad.pack(anchor="w", pady=(0, 6))

    # Panel de resultado
    panel_resultado = tk.Frame(card, bg="#020617")
    panel_resultado.pack(fill="x", padx=20, pady=(0, 8))

    box_result = tk.Frame(panel_resultado, bg="#111827")
    box_result.pack(fill="x")

    lbl_r_title = tk.Label(box_result, text="Resultado",
                           bg="#111827", fg="#93c5fd",
                           font=("Segoe UI", 10, "bold"))
    lbl_r_title.pack(anchor="w", pady=(6, 2))

    lbl_contra = tk.Label(box_result, textvariable=texto_contraseña,
                          bg="#111827", fg="#a5b4fc",
                          font=("Segoe UI", 11, "bold"))
    lbl_contra.pack(anchor="w", pady=(0, 6))

    # Botón
    def boton_conectar_callback():
        texto_estado.set("Conectando al servidor...")
        texto_contraseña.set("Contraseña encontrada: -")
        texto_tiempo.set("Tiempo: 0.0 s")
        texto_velocidad.set("Velocidad: -")
        hilo = threading.Thread(
            target=hilo_cliente_principal,
            args=(root,
                  (texto_estado, texto_hash, texto_rango,
                   texto_intentos, texto_contraseña,
                   texto_tiempo, texto_velocidad),
                  boton_conectar),
            daemon=True
        )
        hilo.start()

    style.configure("Accent.TButton",
                    font=("Segoe UI", 10, "bold"),
                    padding=6)

    boton_conectar = ttk.Button(
        card,
        text="Conectar y empezar fuerza bruta",
        style="Accent.TButton",
        command=boton_conectar_callback
    )
    boton_conectar.pack(pady=(4, 15))

    root.mainloop()


if __name__ == "__main__":
    crear_interfaz_cliente()

import socket
import threading
import time
import json
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox


HOST = "127.0.0.1"
PORT = 5000

tareas = []
candado_tareas = threading.Lock()

clientes_conectados = []
candado_clientes = threading.Lock()

servidor_activo = False
socket_servidor = None
contador_clientes = 0

hash_objetivo = ""
bandera_contraseña_encontrada = threading.Event()

ventana = None
estado_servidor_var = None
contraseña_encontrada_var = None
entrada_contraseña_plana = None
arbol_tareas = None
lista_clientes = None
caja_log = None
entrada_longitud_contraseña = None 



# ===================== UTILIDADES JSON =====================

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


# ===================== GESTIÓN DE TAREAS =====================

def inicializar_tareas_y_hash(contraseña_plana, longitud_texto):
    global hash_objetivo, tareas

    if not contraseña_plana:
        messagebox.showwarning("Advertencia", "Debes escribir una contraseña objetivo.")
        return

    try:
        longitud = int(longitud_texto)
        if longitud < 1:
            raise ValueError
    except ValueError:
        messagebox.showwarning(
            "Advertencia",
            "La longitud debe ser un número entero mayor o igual a 1."
        )
        return

    tareas = []
    bandera_contraseña_encontrada.clear()

    with candado_clientes:
        num_clientes = len(clientes_conectados)

    if num_clientes < 1:
        messagebox.showwarning(
            "Sin clientes",
            "Debe haber al menos un cliente conectado antes de configurar el hash."
        )
        return

    hash_objetivo = hashlib.sha256(contraseña_plana.encode("utf-8")).hexdigest()

    alfabeto = [chr(c) for c in range(ord('a'), ord('z') + 1)]
    total = len(alfabeto)
    base = total // num_clientes
    extra = total % num_clientes

    tareas_dinamicas = []
    idx = 0
    id_tarea = 1

    for i in range(num_clientes):
        tam = base + (1 if i < extra else 0)
        letras = alfabeto[idx: idx + tam]
        idx += tam

        if len(letras) == 0:
            continue

        inicio = letras[0] + ("a" * (longitud - 1))
        fin = letras[-1] + ("z" * (longitud - 1))

        tareas_dinamicas.append({
            "id_tarea": id_tarea,
            "inicio": inicio,
            "fin": fin,
            "longitud": longitud,
            "estado": "pendiente",
            "cliente": ""
        })

        id_tarea += 1

    tareas = tareas_dinamicas
    actualizar_tabla_tareas()

    agregar_log("Estado limpiado. Preparando nuevas tareas...")

    contraseña_encontrada_var.set("Contraseña encontrada: -")
    estado_servidor_var.set(
        f"Hash configurado (longitud = {longitud}). Hash objetivo: {hash_objetivo}"
    )
    agregar_log(
        f"Hash configurado para contraseña '{contraseña_plana}' (len={longitud}): {hash_objetivo}"
    )



def actualizar_tabla_tareas():
    if arbol_tareas is None:
        return

    for item in arbol_tareas.get_children():
        arbol_tareas.delete(item)

    with candado_tareas:
        for tarea in tareas:
            arbol_tareas.insert(
                "",
                "end",
                iid=str(tarea["id_tarea"]),
                values=(
                    tarea["id_tarea"],
                    tarea["inicio"],
                    tarea["fin"],
                    tarea["longitud"],
                    tarea["estado"],
                    tarea["cliente"] if tarea["cliente"] else "-"
                )
            )


def actualizar_estado_tarea(id_tarea, nuevo_estado, nombre_cliente=""):
    with candado_tareas:
        for tarea in tareas:
            if tarea["id_tarea"] == id_tarea:
                tarea["estado"] = nuevo_estado
                if nombre_cliente:
                    tarea["cliente"] = nombre_cliente
                break
    ventana.after(0, actualizar_tabla_tareas)


def asignar_tarea_a_cliente(nombre_cliente):
    if bandera_contraseña_encontrada.is_set():
        return None

    with candado_tareas:
        for tarea in tareas:
            if tarea["estado"] == "pendiente":
                tarea["estado"] = "asignada"
                tarea["cliente"] = nombre_cliente
                ventana.after(0, actualizar_tabla_tareas)
                return tarea
    return None


# ===================== GESTIÓN DE CLIENTES =====================

def agregar_cliente(nombre_cliente, direccion):
    global contador_clientes

    with candado_clientes:
        contador_clientes += 1
        cliente_info = {
            "id": contador_clientes,
            "nombre": nombre_cliente,
            "direccion": f"{direccion[0]}:{direccion[1]}",
        }
        clientes_conectados.append(cliente_info)

    def actualizar_lista():
        lista_clientes.delete(0, tk.END)
        for c in clientes_conectados:
            lista_clientes.insert(
                tk.END,
                f"[{c['id']}] {c['nombre']} @ {c['direccion']}"
            )

    ventana.after(0, actualizar_lista)


def agregar_log(texto):
    if caja_log is None:
        return
    caja_log.insert(tk.END, texto + "\n")
    caja_log.see(tk.END)


# ===================== MANEJO DE CADA CLIENTE =====================

def atender_cliente(conexion, direccion):
    try:
        mensaje_inicial = recibir_json(conexion)

        if mensaje_inicial is None:
            conexion.close()
            return

        nombre_cliente = mensaje_inicial.get("cliente_id", "cliente_desconocido")
        ventana.after(0, agregar_log, f"Cliente conectado: {nombre_cliente} desde {direccion}")
        ventana.after(0, agregar_cliente, nombre_cliente, direccion)

        while not hash_objetivo:
            ventana.after(0, agregar_log, f"{nombre_cliente} esperando configuración del hash...")
            time.sleep(0.5)

        tarea = asignar_tarea_a_cliente(nombre_cliente)
        if tarea is None:
            enviar_json(conexion, {"tipo": "sin_tarea"})
            ventana.after(0, agregar_log, f"Sin tareas disponibles para {nombre_cliente}.")
            conexion.close()
            return

        mensaje_tarea = {
            "tipo": "tarea",
            "id_tarea": tarea["id_tarea"],
            "inicio": tarea["inicio"],
            "fin": tarea["fin"],
            "longitud": tarea["longitud"],
            "hash": hash_objetivo
        }
        enviar_json(conexion, mensaje_tarea)
        ventana.after(0, agregar_log, f"Tarea {tarea['id_tarea']} asignada a {nombre_cliente}.")

        while True:
            msg = recibir_json(conexion)
            if msg is None:
                ventana.after(0, agregar_log, f"Cliente desconectado: {nombre_cliente}.")
                break

            tipo = msg.get("tipo")
            if tipo == "encontrado":
                contraseña = msg.get("password", "")
                ventana.after(0, agregar_log,
                              f"¡Contraseña encontrada por {nombre_cliente}!: {contraseña}")
                bandera_contraseña_encontrada.set()
                ventana.after(0, contraseña_encontrada_var.set,
                              f"Contraseña encontrada: {contraseña} (por {nombre_cliente})")
                ventana.after(0, estado_servidor_var.set,
                              "Búsqueda completada: se encontró la contraseña.")
                actualizar_estado_tarea(msg.get("id_tarea", 0), "encontrada", nombre_cliente)
                break

            elif tipo == "terminado":
                id_tarea = msg.get("id_tarea", 0)
                ventana.after(0, agregar_log,
                              f"{nombre_cliente} terminó la tarea {id_tarea} sin encontrar contraseña.")
                actualizar_estado_tarea(id_tarea, "finalizada", nombre_cliente)
                break

    except Exception as e:
        ventana.after(0, agregar_log, f"Error con cliente {direccion}: {e}")
    finally:
        try:
            conexion.close()
        except:
            pass


# ===================== HILO PRINCIPAL DEL SERVIDOR =====================

def hilo_servidor():
    global socket_servidor, servidor_activo

    try:
        socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_servidor.bind((HOST, PORT))
        socket_servidor.listen()
        ventana.after(0, estado_servidor_var.set,
                      f"Servidor escuchando en {HOST}:{PORT}")
        ventana.after(0, agregar_log,
                      f"Servidor iniciado en {HOST}:{PORT}")

        while servidor_activo:
            try:
                conexion, direccion = socket_servidor.accept()
            except OSError:
                break

            hilo = threading.Thread(target=atender_cliente, args=(conexion, direccion), daemon=True)
            hilo.start()

    except OSError as e:
        ventana.after(0, messagebox.showerror,
                      "Error de servidor", f"No se pudo iniciar el servidor:\n{e}")
        ventana.after(0, estado_servidor_var.set, "Error al iniciar el servidor.")
    finally:
        if socket_servidor:
            try:
                socket_servidor.close()
            except:
                pass
        socket_servidor = None
        servidor_activo = False
        ventana.after(0, estado_servidor_var.set, "Servidor detenido.")


# ===================== ACCIONES DE LA GUI =====================

def accion_configurar_hash():
    """
    Lee la contraseña en texto plano y la longitud desde la GUI,
    y configura el hash y las tareas.
    """
    contraseña_plana = entrada_contraseña_plana.get().strip()
    longitud_texto = entrada_longitud_contraseña.get().strip()
    if not longitud_texto:
        longitud_texto = "3"  # valor por defecto
    inicializar_tareas_y_hash(contraseña_plana, longitud_texto)

def accion_iniciar_servidor():
    global servidor_activo
    if servidor_activo:
        messagebox.showinfo("Servidor", "El servidor ya está en ejecución.")
        return


    bandera_contraseña_encontrada.clear()
    servidor_activo = True
    hilo = threading.Thread(target=hilo_servidor, daemon=True)
    hilo.start()
    estado_servidor_var.set("Servidor iniciando...")


def accion_detener_servidor():
    global servidor_activo, socket_servidor
    if not servidor_activo:
        messagebox.showinfo("Servidor", "El servidor ya está detenido.")
        return

    servidor_activo = False
    if socket_servidor:
        try:
            socket_servidor.close()
        except:
            pass
    estado_servidor_var.set("Deteniendo servidor...")
    agregar_log("Servidor detenido manualmente.")


# ===================== INTERFAZ GRÁFICA (DARK MODE) =====================

def crear_interfaz_servidor():
    global ventana, estado_servidor_var, contraseña_encontrada_var
    global entrada_contraseña_plana, arbol_tareas, lista_clientes, caja_log

    ventana = tk.Tk()
    ventana.title("Servidor Fuerza Bruta Distribuida")
    ventana.geometry("980x520")
    ventana.configure(bg="#020617")

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except:
        pass

    BG_MAIN = "#020617"
    BG_CARD = "#0f172a"
    BG_PANEL = "#111827"
    FG_TEXT = "#e5e7eb"
    FG_MUTED = "#9ca3af"
    FG_ACCENT = "#93c5fd"

    card = tk.Frame(ventana, bg=BG_CARD, bd=1, relief="ridge")
    card.pack(expand=True, fill="both", padx=20, pady=20)

    estado_servidor_var = tk.StringVar(value="Servidor detenido.")
    contraseña_encontrada_var = tk.StringVar(value="Contraseña encontrada: -")

    lbl_titulo = tk.Label(
        card,
        text="Servidor de Fuerza Bruta Distribuida",
        bg=BG_CARD,
        fg=FG_TEXT,
        font=("Segoe UI", 18, "bold")
    )
    lbl_titulo.pack(pady=(10, 8))

    panel_superior = tk.Frame(card, bg=BG_CARD)
    panel_superior.pack(fill="x", padx=20, pady=(0, 8))

    box_config = tk.Frame(panel_superior, bg=BG_PANEL)
    box_config.pack(fill="x", side="left", expand=True)

    lbl_conf_title = tk.Label(box_config, text="Configuración",
                              bg=BG_PANEL, fg=FG_ACCENT,
                              font=("Segoe UI", 10, "bold"))
    lbl_conf_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))

    tk.Label(box_config, text="Contraseña objetivo (texto plano):",
         bg=BG_PANEL, fg=FG_TEXT).grid(row=1, column=0, sticky="w", padx=8, pady=2)

    entrada_contraseña_plana = tk.Entry(box_config, width=20,
                                        bg="#020617", fg=FG_TEXT, insertbackground=FG_TEXT,
                                        relief="flat")
    entrada_contraseña_plana.grid(row=1, column=1, padx=4, pady=2, sticky="w")

    btn_configurar = ttk.Button(box_config, text="Configurar hash y tareas",
                                command=accion_configurar_hash)
    btn_configurar.grid(row=1, column=2, padx=6, pady=2)

    tk.Label(box_config, text="Longitud (número de caracteres):",
            bg=BG_PANEL, fg=FG_TEXT).grid(row=2, column=0, sticky="w", padx=8, pady=2)

    global entrada_longitud_contraseña
    entrada_longitud_contraseña = tk.Spinbox(
        box_config,
        from_=1,
        to=8,
        width=5,
        bg="#020617",
        fg=FG_TEXT,
        insertbackground=FG_TEXT,
        relief="flat"
    )
    entrada_longitud_contraseña.delete(0, tk.END)
    entrada_longitud_contraseña.insert(0, "3")  # valor por defecto
    entrada_longitud_contraseña.grid(row=2, column=1, padx=4, pady=2, sticky="w")

    btn_iniciar = ttk.Button(box_config, text="Iniciar servidor",
                            command=accion_iniciar_servidor)
    btn_iniciar.grid(row=3, column=0, padx=8, pady=6, sticky="w")

    btn_detener = ttk.Button(box_config, text="Detener servidor",
                            command=accion_detener_servidor)
    btn_detener.grid(row=3, column=1, padx=4, pady=6, sticky="w")


    lbl_estado = tk.Label(box_config, textvariable=estado_servidor_var,
                        bg=BG_PANEL, fg=FG_MUTED, anchor="w", wraplength=550)
    lbl_estado.grid(row=4, column=0, columnspan=3, sticky="w", padx=8, pady=(2, 2))

    lbl_contra = tk.Label(box_config, textvariable=contraseña_encontrada_var,
                        bg=BG_PANEL, fg="#a5b4fc", anchor="w")
    lbl_contra.grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 6))


    panel_central = tk.Frame(card, bg=BG_CARD)
    panel_central.pack(fill="both", expand=True, padx=20, pady=(0, 8))

    marco_tareas = tk.Frame(panel_central, bg=BG_PANEL)
    marco_tareas.pack(side="left", fill="both", expand=True, padx=(0, 6))

    lbl_tareas = tk.Label(marco_tareas, text="Tareas",
                          bg=BG_PANEL, fg=FG_ACCENT,
                          font=("Segoe UI", 10, "bold"))
    lbl_tareas.pack(anchor="w", padx=8, pady=(6, 2))

    columnas = ("id", "inicio", "fin", "longitud", "estado", "cliente")
    arbol_tareas = ttk.Treeview(marco_tareas, columns=columnas, show="headings", height=10)

    style.configure("Treeview",
                    background=BG_PANEL,
                    fieldbackground=BG_PANEL,
                    foreground=FG_TEXT,
                    rowheight=22)
    style.configure("Treeview.Heading",
                    background="#1f2937",
                    foreground=FG_TEXT,
                    font=("Segoe UI", 9, "bold"))
    style.map("Treeview", background=[("selected", "#1d4ed8")])

    arbol_tareas.heading("id", text="ID")
    arbol_tareas.heading("inicio", text="Inicio")
    arbol_tareas.heading("fin", text="Fin")
    arbol_tareas.heading("longitud", text="Len")
    arbol_tareas.heading("estado", text="Estado")
    arbol_tareas.heading("cliente", text="Cliente")

    arbol_tareas.column("id", width=40, anchor="center")
    arbol_tareas.column("inicio", width=70, anchor="center")
    arbol_tareas.column("fin", width=70, anchor="center")
    arbol_tareas.column("longitud", width=50, anchor="center")
    arbol_tareas.column("estado", width=100, anchor="center")
    arbol_tareas.column("cliente", width=140, anchor="center")

    arbol_tareas.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    marco_clientes = tk.Frame(panel_central, bg=BG_PANEL)
    marco_clientes.pack(side="right", fill="y", padx=(6, 0))

    lbl_clientes = tk.Label(marco_clientes, text="Clientes conectados",
                            bg=BG_PANEL, fg=FG_ACCENT,
                            font=("Segoe UI", 10, "bold"))
    lbl_clientes.pack(anchor="w", padx=8, pady=(6, 2))

    lista_clientes = tk.Listbox(marco_clientes, height=12,
                                bg="#020617", fg=FG_TEXT,
                                selectbackground="#1d4ed8",
                                borderwidth=0, highlightthickness=0)
    lista_clientes.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    marco_log = tk.Frame(card, bg=BG_PANEL)
    marco_log.pack(fill="both", expand=True, padx=20, pady=(0, 12))

    lbl_log = tk.Label(marco_log, text="Registro (log)",
                       bg=BG_PANEL, fg=FG_ACCENT,
                       font=("Segoe UI", 10, "bold"))
    lbl_log.pack(anchor="w", padx=8, pady=(6, 2))

    caja_log = tk.Text(marco_log, height=6,
                       bg="#020617", fg=FG_TEXT,
                       insertbackground=FG_TEXT,
                       borderwidth=0, highlightthickness=0)
    caja_log.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    ventana.mainloop()


if __name__ == "__main__":
    crear_interfaz_servidor()

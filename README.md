# Laboratorio 3: Sistema Cliente–Servidor para Fuerza Bruta Distribuida  
**Python – Sockets – Threads – SHA-256**

Este laboratorio implementa un sistema distribuido donde varios clientes colaboran para encontrar una contraseña mediante **fuerza bruta**. El servidor asigna tareas y cada cliente calcula hashes SHA-256 usando múltiples hilos.

---

## Integrantes  
- **Manuela Maiguel**  
- **Alejandro Cantillo**
- **Yulissa Tapia**  

## Curso  
- Estructuras de Datos 2
- *Universisas del Norte*

---

# 1. Descripción General del Proyecto  

Este laboratorio implementa un sistema cliente–servidor que distribuye el trabajo de encontrar una contraseña mediante **fuerza bruta**.  
El servidor divide el espacio de búsqueda en rangos y los asigna a los clientes.  
Cada cliente utiliza **múltiples hilos** para generar cadenas posibles, calcular su hash SHA-256 y compararlo con el hash objetivo.  

Cuando un cliente encuentra la contraseña correcta, envía el resultado al servidor, quien detiene el procesamiento del resto de tareas.

El proyecto permite comprender conceptos como:

- Computación distribuida
- Comunicación mediante sockets TCP
- Coordinación entre procesos
- Paralelismo con hilos
- Hashing criptográfico

---

# 2. Arquitectura del Sistema (Descripción)

El sistema está compuesto por un **servidor central** y múltiples **clientes** que trabajan en paralelo:

- El **servidor** administra una lista de tareas, donde cada una define un rango de contraseñas posibles según su longitud y límites lexicográficos.
- Cada cliente, al conectarse, solicita una tarea. Si hay tareas disponibles, recibe un rango específico de búsqueda y el hash objetivo.
- Una vez asignada la tarea, el cliente lanza varios hilos que recorren el espacio de claves dentro de ese rango, probando todas las combinaciones posibles.
- Si algún hilo descubre la contraseña, el cliente lo reporta al servidor inmediatamente.
- Si el cliente finaliza su rango sin encontrar la clave, notifica al servidor que la tarea fue completada sin éxito.
- El servidor continúa aceptando clientes y asignando tareas hasta que todas se hayan entregado.
- El proceso termina cuando la contraseña es encontrada o cuando se agotan todas las tareas.

Este enfoque permite que varios clientes distribuyan la carga de trabajo, acelerando el proceso de fuerza bruta mediante paralelismo distribuido.

---

# 3. Archivos del Proyecto

### **server.py**  
Encargado de:
- Recibir conexiones entrantes  
- Asignar tareas disponibles  
- Manejar la concurrencia con `threading.Thread`  
- Recibir resultados de los clientes  
- Enviar mensajes JSON mediante sockets  

El servidor define previamente:
- Una lista de tareas
- Un hash objetivo calculado con SHA-256

### **client.py**  
El cliente:
- Se conecta al servidor
- Recibe una tarea
- Inicia cuatro hilos paralelos para realizar fuerza bruta
- Calcula hash SHA-256 por cada cadena generada
- Detiene el proceso cuando encuentra la contraseña o cuando termina su rango

Para coordinar los hilos usa:

contraseña_encontrada = threading.Event()

---

# 4. Funcionamiento del Sistema

- 1. Ejecutar el servidor:


python server.py

El servidor quedará escuchando conexiones de manera indefinida.

- 2. Ejecutar clientes:
En una o varias terminales:


python client.py

Cada cliente imprime mensajes mostrando el progreso:
- Conexión al servidor
- Rango recibido
- Avance de hilos
- Resultado final

Cuando encuentra la contraseña, envía:


{"tipo": "encontrado", "id_tarea": X, "password": "abc"}

---

# 5. Tecnologías y Conceptos Implementados

- Python 3
- Sockets TCP
- Concurrencia con hilos (threading)
- Comunicación estructurada con JSON
- Hashing SHA-256 (hashlib)
- Generación de combinaciones (itertools.product)
- Sincronización entre hilos con eventos y locks

---

# 6. Posibles Errores y Soluciones

- 1. Error: “Address already in use”
Ocurre si el servidor no cerró correctamente o si intentas iniciar dos servidores en el mismo puerto.
Solución:
Cambiar el puerto o esperar a que el sistema libere el puerto.

- 2. Cliente se desconecta inesperadamente
Puede suceder si el cliente se cierra abruptamente o hay problemas de red.
Solución:
El servidor ya maneja este caso detectando None al recibir datos y cerrando la conexión limpiamente.

- 3. Formato JSON incorrecto
Si el cliente no envía un JSON válido, la función recibir_json retornará None.
Solución:
Validar siempre el formato del mensaje en el cliente antes de enviarlo.

- 4. Condiciones de carrera
Pueden ocurrir si varios clientes intentan obtener tareas al mismo tiempo.
Solución:
Se utiliza correctamente threading.Lock para sincronizar acceso a la lista de tareas.

---

# 7. Conclusiones

- El laboratorio permitió aprender:
- Cómo dividir un problema computacional en tareas distribuidas
- Cómo usar sockets para coordinar computación entre distintos procesos
- Cómo aplicar hilos para acelerar el procesamiento local
- Cómo manejar sincronización entre hilos y entre procesos
- Cómo validar claves mediante hashing criptográfico


Este proyecto es aplicable a sistemas de cómputo distribuido, criptografía y tareas de alto costo computacional.


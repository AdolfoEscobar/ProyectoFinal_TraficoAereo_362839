# Guía de exposición — Proyecto Final (362839)

Cómo presentar y explicar el proyecto en clase, paso a paso.
Duración sugerida: 10–12 minutos + preguntas.

## 1. Idea en 30 segundos (di esto para abrir)

> "Mi proyecto analiza el tráfico aéreo junto con el clima usando datos de
> la nube. Descarga vuelos, sensores ambientales, clima y calidad del aire;
> los procesa con cómputo paralelo —asyncio, MPI, Numba y Pandas— y responde
> con datos si el clima provoca retrasos en los vuelos."

## 2. Estructura sugerida

| Bloque | Tiempo | Qué muestras |
|---|---|---|
| Problema y preguntas | 1 min | Las 5 preguntas del PDF |
| Arquitectura | 1 min | Diagrama de abajo |
| Demo en vivo | 4 min | `main.py` corriendo (8 pasos) |
| Código clave | 3 min | 4 fragmentos (uno por tecnología) |
| Resultados y cierre | 2 min | Gráficas + respuestas + justificación APIs |

## 3. Arquitectura (dibújala o descríbela así)

```
AirLabs + ThingSpeak + OpenWeather + OpenAQ   (nube)
        |  descarga concurrente con asyncio
        v
Limpieza con Pandas  -->  1500 vuelos, 200 lecturas en vivo
        |
        +--> Análisis Pandas (12 análisis + 5 respuestas)
        +--> Numba (atípicos acelerados, ~128x)
        +--> MPI 4 procesos (scatter/gather, verificado)
        v
8 gráficas + reporte PDF
```

Frase: "Los datos entran por clientes asíncronos, se limpian con Pandas, se
analizan en tres motores paralelos y salen como gráficas y reporte."

## 4. Demo en vivo (el corazón de la presentación)

Ejecuta:

```bash
./.venv/bin/python main.py
```

Mientras corre, narra cada paso (sale numerado del 1 al 8):

1. **Descarga concurrente:** "Aquí se ven las 4 fuentes y su origen: sensores
   en vivo de ThingSpeak, lo demás simulado porque AirLabs me dejó en
   waitlist. El speedup de asyncio fue 1.68x en red real."
2. **Limpieza:** "Pandas normaliza tipos, quita duplicados y guarda los CSV."
3. **Análisis de vuelos:** señala hora pico (13:00), cancelados (89) y la
   tabla de retrasos por aeropuerto. "Son los 12 análisis del documento."
4. **Ambiental:** "Estadísticos de los sensores en vivo y clima por ciudad."
5. **Aceleración:** "Numba es ~128 veces más rápido que Python puro; el motor
   se elige solo: CuPy si hay GPU, Numba si no."
6. **MPI:** "Si mpiexec funciona aquí, reparte en 4 procesos; si no, el
   sistema sigue con 1 y lo dice. La verificación dio CORRECTO."
7. **Gráficas:** "Se generan 8 PNG automáticamente."
8. **Respuestas:** lee las 5 respuestas. Es tu cierre fuerte.

Luego abre 2–3 PNG de `resultados/` (clima-retrasos, velocidad-altitud con
los puntos rojos, actividad por hora).

## 5. Código clave (muestra un fragmento de cada uno)

**a) asyncio — `datos/descarga.py`:** `asyncio.gather(...)` con las 4
descargas. Di: "Las cuatro peticiones avanzan al mismo tiempo mientras
esperan red, en vez de una por una. Por eso medimos secuencial contra
concurrente."

**b) Pandas — `procesamiento/analisis.py`:** `relacion_clima_retrasos()`.
Di: "Agrupa por condición climática con groupby y calcula la correlación
lluvia-retraso: 0.55, positiva."

**c) Numba — `procesamiento/aceleracion.py`:** `@njit` sobre `_zscore_nb`.
Di: "Este decorador compila la función a código máquina. El benchmark compara
Python puro, NumPy y Numba con tiempos reales: Numba gana por ~128x."

**d) MPI — `procesamiento/mpi_analisis.py`:** `comm.scatter`, cálculo local,
`comm.gather`. Di: "El proceso 0 reparte los 1500 vuelos, cada proceso saca
parciales de su parte y el 0 los combina y verifica contra Pandas."

**e) Honestidad del sistema — `datos/clientes.py`:** cada función devuelve
`(DataFrame, fuente)`. Di: "Cada resultado dice de dónde salió: en vivo o
simulado. Nada se finge."

## 6. Si te preguntan (respuestas listas)

- **¿Por qué datos simulados?** "AirLabs me puso en waitlist antes de la
  entrega. El sistema intenta la API real primero y cae a simulación
  realista y determinista, etiquetando la fuente. Con la clave en el .env se
  re-ejecuta sin cambiar código. ThingSpeak sí está en vivo."
- **¿Qué es scatter/gather?** "Scatter reparte datos del proceso 0 a todos;
  gather los reúne de vuelta. Cada proceso trabaja su parte sin hablar con
  los demás."
- **¿Qué es el z-score?** "A cuántas desviaciones está un dato de la media.
  Si pasa de 3, lo marco atípico: así detecté el avión a 150 km/h y el de
  500 ft."
- **¿Por qué no CuPy?** "CuPy necesita GPU NVIDIA y esta Mac no tiene. Mi
  código lo intenta primero y usa Numba si no existe; en una PC con CUDA
  correría en GPU sin cambios."
- **¿Para qué la semilla 362839?** "Para que los datos simulados sean
  reproducibles: cada ejecución da los mismos resultados."
- **¿Qué aporta cada tecnología?** "asyncio acelera la red, MPI reparte el
  trabajo entre procesos, Numba acelera el cálculo, Pandas analiza las
  tablas."

## 7. Plan B (si algo falla en vivo)

- Si no hay internet: el sistema cae a simulado solo y sigue. Di: "Justo por
  eso tiene doble modo."
- Si `main.py` tarda: mientras corre, explica la arquitectura.
- Si MPI falla: el programa lo dice y usa 1 proceso; muestra
  `resultados/mpi_4procesos_log.txt` como evidencia de la corrida de 4.
- Lleva el PDF abierto: sección 4 trae la bitácora y la 5 las gráficas.

## 8. Cierre (últimos 30 segundos)

> "En resumen: sistema completo que descarga de la nube, procesa en paralelo
> con cuatro tecnologías medidas, y responde con datos que la lluvia sí
> aumenta los retrasos: 32.8 contra 8 minutos. Gracias; ¿preguntas?"

## 9. Archivos por si piden ver estructura

- `main.py` — pipeline de 8 pasos (punto de entrada)
- `config.py` — rutas, claves, canales, parámetros
- `datos/` — clientes async + generador simulado
- `procesamiento/` — Pandas + Numba/CuPy + MPI
- `visualizacion/` — Matplotlib + tablero Streamlit opcional
- `pruebas/` — 7 pruebas sin red
- `reporte/` — generador + PDF final
- `resultados/` — todas las evidencias

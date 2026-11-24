# Proyecto Final — Análisis de tráfico aéreo y condiciones ambientales

**Alumno:** Adolfo Escobar Pereyra · **Matrícula:** 362839
**Materia:** Cómputo Paralelo y Distribuido · **Docente:** Jose Saul De Lira Montañez

Sistema que descarga datos de vuelos y sensores ambientales desde la nube,
los procesa con tecnologías de cómputo paralelo y responde las 5 preguntas
de análisis del proyecto.

## Fuentes de datos

| Fuente | Datos | Acceso |
|---|---|---|
| AirLabs | Vuelos, horarios, retrasos, aeronaves | API key (o simulado) |
| ThingSpeak | Sensores: temp., humedad, presión, viento, luz, lluvia | Canales públicos en vivo |
| OpenWeather | Clima actual por ciudad | API key (o simulado) |
| OpenAQ | Calidad del aire (PM2.5, PM10, O₃, NO₂) | API key (o simulado) |

Sin claves, el sistema trabaja en **modo demostración** con datos simulados
realistas y reproducibles (semilla fija); ThingSpeak siempre intenta primero
los canales públicos reales. Cada resultado indica su fuente.

## Tecnologías de cómputo paralelo

- **asyncio + aiohttp:** descarga concurrente de APIs (se mide secuencial vs. concurrente).
- **MPI4Py:** reparto de vuelos con scatter/gather entre N procesos, con verificación contra el cálculo secuencial.
- **Numba (+ CuPy si hay GPU NVIDIA):** detección de atípicos y haversine acelerados, con benchmark Python vs. NumPy vs. Numba.
- **Pandas:** limpieza y análisis tabular. **Matplotlib:** 8 gráficas (+ tablero Streamlit opcional).

## Instalación

```bash
cd ProyectoFinal_TraficoAereo_362839
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
# Para MPI multiproceso también se necesita OpenMPI (mpiexec):
brew install open-mpi   # macOS
```

Para datos reales de AirLabs/OpenWeather/OpenAQ (opcional):

```bash
cp .env.ejemplo .env   # y escribe tus claves dentro
```

## Uso

```bash
./.venv/bin/python main.py            # pipeline completo paso a paso (8 pasos)
./.venv/bin/python pruebas/test_analisis.py   # pruebas sin red
mpiexec -n 4 ./.venv/bin/python -m procesamiento.mpi_analisis  # demo MPI
./.venv/bin/python reporte/generar_reporte.py  # genera el reporte PDF
```

Todo lo que genera el sistema queda en `resultados/`: tablas CSV, resumen
JSON, 8 gráficas PNG, bitácora de ejecución y evidencia MPI.

## Estructura

```
main.py                  # pipeline de 8 pasos (punto de entrada)
config.py                # rutas, claves, canales y parámetros
datos/
  clientes.py            # clientes async: AirLabs, ThingSpeak, OpenWeather, OpenAQ
  descarga.py            # orquestador asyncio + benchmark secuencial/concurrente
  generador.py           # datos simulados realistas (modo demostración)
procesamiento/
  analisis.py            # 12 análisis de vuelos + sensores + 5 respuestas
  aceleracion.py         # CuPy/Numba/NumPy + benchmark
  mpi_analisis.py        # scatter/gather con verificación
visualizacion/
  graficas.py            # 8 gráficas Matplotlib
  app_streamlit.py       # tablero opcional (streamlit run ...)
pruebas/test_analisis.py # 7 pruebas sin red
reporte/generar_reporte.py  # construye el PDF del reporte
resultados/              # evidencias generadas al ejecutar
```

## Resultados principales (ejecución de referencia)

- **asyncio:** 1.50x–2.28x más rápido en canales con red real (varía por red).
- **Numba:** ~128x vs. Python puro en detección de atípicos (300 mil datos).
- **MPI (4 procesos):** 375 vuelos por proceso, resultado idéntico al secuencial ✔.
- **Clima–retrasos:** 32.8 min con lluvia vs. 8.0 min despejado; correlación lluvia–retraso ≈ 0.55.
- **Hora pico:** 13:00 h. **Aeropuerto con más retraso promedio:** TIJ (15.6 min).

Ver el detalle en `reporte/Reporte_ProyectoFinal_TraficoAereo_AdolfoEscobar_362839.pdf`.

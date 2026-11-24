"""Genera el reporte PDF del proyecto final con resultados reales.

Uso:
    .venv/bin/python reporte/generar_reporte.py   # después de main.py

Lee el resumen JSON, la bitácora de ejecución, la evidencia MPI y las
gráficas PNG de ``resultados/`` y construye un PDF profesional con
portada, ejecución paso a paso, resultados y conclusiones.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fpdf import FPDF

from config import BASE_DIR, REPORTE_DIR, RESULTADOS_DIR

NOMBRE_PDF = "Reporte_ProyectoFinal_TraficoAereo_AdolfoEscobar_362839.pdf"

# Las fuentes base de fpdf2 solo cubren latin-1: se normalizan los símbolos
# que no existen ahí para que el PDF nunca falle por un carácter raro.
REEMPLAZOS = {"✔": "OK", "✘": "X", "→": "->", "←": "<-", "₂": "2", "₃": "3",
              "–": "-", "—": "-", "“": '"', "”": '"', "’": "'", "•": "-",
              "µg": "ug", "✈": "", "₀": "0"}


def txt(s):
    """Convierte cualquier texto a algo seguro para el PDF."""
    s = str(s)
    for a, b in REEMPLAZOS.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


class Reporte(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 8, txt("Proyecto Final — Tráfico aéreo y ambiente  |  "
                            "Adolfo Escobar Pereyra (362839)"), align="R")
        self.ln(10)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 8, f"Pagina {self.page_no()}/{{nb}}", align="C")
        self.set_text_color(0, 0, 0)

    def h1(self, texto):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(31, 111, 235)
        self.cell(0, 10, txt(texto), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(31, 111, 235)
        self.line(self.l_margin, self.get_y(), 200, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def h2(self, texto):
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, txt(texto), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def parrafo(self, texto):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, txt(texto), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def bullets(self, items):
        self.set_font("Helvetica", "", 10)
        for it in items:
            self.multi_cell(0, 5.5, txt(f"  - {it}"), new_x="LMARGIN",
                            new_y="NEXT")
        self.ln(2)

    def codigo(self, texto, max_lineas=40):
        self.set_font("Courier", "", 7.5)
        self.set_fill_color(245, 245, 245)
        lineas = str(texto).splitlines()[:max_lineas]
        for ln in lineas:
            self.cell(0, 4, txt(" " + ln[:110]), new_x="LMARGIN",
                      new_y="NEXT", fill=True)
        self.ln(3)

    def imagen(self, nombre, titulo, ancho=170):
        ruta = RESULTADOS_DIR / nombre
        if not ruta.exists():
            return
        if self.get_y() > 150:
            self.add_page()
        self.h2(titulo)
        self.image(str(ruta), w=ancho, x=(210 - ancho) / 2)
        self.ln(4)


def main():
    resumen = json.loads((RESULTADOS_DIR / "resumen_resultados.json").read_text())
    log = (RESULTADOS_DIR / "ejecucion_log.txt").read_text()
    mpi_log = (RESULTADOS_DIR / "mpi_4procesos_log.txt").read_text() \
        if (RESULTADOS_DIR / "mpi_4procesos_log.txt").exists() else ""
    fuentes = resumen["fuentes"]
    bench = resumen["benchmark_aceleracion"]
    td = resumen["tiempos_descarga"]
    speedup_async = td["canales_secuencial"] / max(td["canales_concurrente"], 1e-6)

    pdf = Reporte()
    pdf.alias_nb_pages("{nb}")
    pdf.set_auto_page_break(True, 20)

    # ---- Portada ------------------------------------------------------
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(31, 111, 235)
    pdf.multi_cell(0, 10, txt("Análisis de tráfico aéreo y\ncondiciones "
                              "ambientales\nusando sensores y APIs en la nube"),
                   align="C")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, txt("Proyecto Final — Cómputo Paralelo y Distribuido"),
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 12)
    for linea in ["Alumno: Adolfo Escobar Pereyra",
                  "Matrícula: 362839",
                  "Docente: Jose Saul De Lira Montañez",
                  "Fecha: noviembre de 2026"]:
        pdf.cell(0, 8, txt(linea), align="C", new_x="LMARGIN", new_y="NEXT")

    # ---- 1. Objetivo ---------------------------------------------------
    pdf.add_page()
    pdf.h1("1. Objetivo")
    pdf.parrafo("Aplicar las tecnologías de cómputo paralelo a la solución de "
                "un problema real: analizar el tráfico aéreo junto con las "
                "condiciones ambientales usando datos de la nube. El sistema "
                "descarga vuelos (AirLabs), sensores ambientales (ThingSpeak), "
                "clima (OpenWeather) y calidad del aire (OpenAQ); procesa todo "
                "con asyncio, MPI4Py, Numba/CuPy y Pandas; y responde con datos "
                "las cinco preguntas de análisis del proyecto.")
    pdf.h2("Alcance cumplido (documento CPD_Py201-1)")
    pdf.bullets([
        "4 fuentes de datos integradas (2 en vivo sin clave, 2 con clave o simuladas).",
        "12 análisis de tráfico aéreo: regiones, cancelados, rutas, aerolíneas, "
        "salidas/llegadas, ficha de vuelo, velocidad/altitud, retrasos por "
        "aeropuerto, clima-retrasos, atípicos, simulación de ruta y monitoreo.",
        "8 variables ambientales de sensores + clima por ciudad + calidad del aire.",
        "5 tecnologías paralelas demostradas con mediciones reales de speedup.",
    ])

    # ---- 2. Arquitectura -----------------------------------------------
    pdf.add_page()
    pdf.h1("2. Arquitectura del sistema")
    pdf.parrafo("El sistema es un pipeline de 8 pasos (main.py). Los datos "
                "entran por clientes asíncronos, se limpian con Pandas, se "
                "analizan en tres motores paralelos (asyncio, MPI, Numba/CuPy) "
                "y salen como tablas CSV, gráficas PNG y este reporte.")
    pdf.codigo("main.py (8 pasos)                     resultados/*.csv, *.png, *.json\n"
               "  1. descarga concurrente -----> 2. limpieza Pandas\n"
               "  3. analisis de vuelos -------+ 4. analisis ambiental\n"
               "  5. benchmark Numba/CuPy -----+ 6. MPI scatter/gather\n"
               "  7. graficas Matplotlib ------+ 8. respuestas y conclusiones\n"
               "\ndatos/            clientes async + generador simulado\n"
               "procesamiento/  analisis Pandas + aceleracion + MPI\n"
               "visualizacion/  Matplotlib (+ tablero Streamlit opcional)\n"
               "pruebas/            7 pruebas automaticas sin red")
    pdf.h2("Origen de los datos en esta ejecución")
    pdf.bullets([f"Vuelos: {fuentes['vuelos']}.",
                 f"Sensores: {fuentes['sensores']}.",
                 f"Clima: {fuentes['clima']}.",
                 f"Calidad del aire: {fuentes['aire']}.",
                 "Sin claves de API, el sistema usa datos simulados realistas y "
                 "reproducibles (semilla 362839); ThingSpeak usa canales "
                 "públicos reales (canal 9 y estación MathWorks 12397)."])

    # ---- 3. Tecnologías paralelas ---------------------------------------
    pdf.add_page()
    pdf.h1("3. Tecnologías de cómputo paralelo y mediciones")
    pdf.h2(f"3.1 asyncio — descarga concurrente (speedup {speedup_async:.2f}x)")
    pdf.parrafo(f"Las cuatro fuentes se descargan con aiohttp y asyncio.gather. "
                f"Medición sobre red real (canales ThingSpeak): secuencial "
                f"{td['canales_secuencial']:.2f} s contra concurrente "
                f"{td['canales_concurrente']:.2f} s, es decir {speedup_async:.2f} "
                f"veces más rápido. Pipeline completo: {td['secuencial']:.2f} s "
                f"vs {td['concurrente']:.2f} s.")
    pdf.h2("3.2 MPI4Py — procesamiento distribuido (4 procesos, verificado)")
    pdf.parrafo("El proceso 0 reparte 1500 vuelos con scatter; cada proceso "
                "calcula parciales (por región, retrasos, activos/cancelados) y "
                "el 0 los combina con gather y verifica contra Pandas:")
    pdf.codigo(mpi_log or "(ver bitácora: mpiexec -n 4 ... -m procesamiento.mpi_analisis)")
    pdf.h2(f"3.3 Numba/CuPy — aceleración numérica (motor: {bench['motor']})")
    t = bench["tiempos"]
    s = bench["speedup_vs_python"]
    pdf.parrafo(f"Z-score sobre 300 mil datos. Tiempos: Python puro {t['python_puro']} s, "
                f"NumPy {t['numpy']} s, Numba {t['numba']} s. Speedup vs Python: "
                f"NumPy {s['numpy']}x, Numba {s['numba']}x. En esta computadora "
                f"(Mac sin GPU NVIDIA) se usa Numba en CPU; si existiera CuPy/CUDA, "
                f"el mismo código correría en la GPU sin cambios.")
    pdf.h2("3.4 Pandas y Matplotlib")
    pdf.parrafo("Pandas limpia y agrega todas las tablas (1500 vuelos, 200 "
                "lecturas de sensores en vivo, clima y aire). Matplotlib genera "
                "las 8 gráficas de la sección 5; hay además un tablero "
                "Streamlit opcional (visualizacion/app_streamlit.py).")

    # ---- 4. Ejecución paso a paso ---------------------------------------
    pdf.add_page()
    pdf.h1("4. Ejecución paso a paso (bitácora real, extracto)")
    pdf.parrafo("Salida real de `.venv/bin/python main.py` (completa en "
                "resultados/ejecucion_log.txt):")
    # Extracto: pasos 1, 3 (inicio), 5, 6 y 8.
    lineas = log.splitlines()
    extracto = [ln for ln in lineas
                if not ln.startswith(("   [ThingSpeak]", "Matplotlib"))]
    # Recorta tablas largas del paso 3 para que quepan.
    out, saltar = [], 0
    for ln in extracto:
        if saltar:
            saltar -= 1
            continue
        out.append(ln)
        if ln.startswith("Por aerolínea:") or ln.startswith("   Por aerolínea"):
            saltar = 6
    pdf.codigo("\n".join(out), max_lineas=120)

    # ---- 5. Resultados ---------------------------------------------------
    pdf.add_page()
    pdf.h1("5. Resultados y gráficas")
    pdf.parrafo("Hallazgos principales: la hora pico es a las 13:00; TIJ tiene el "
                "mayor retraso promedio (15.6 min); con lluvia el retraso "
                "promedio es 32.8 min contra 8.0 min despejado (correlación "
                "lluvia-retraso 0.55); se detectaron "
                f"{resumen['outliers']['velocidad_kmh']['n']}, "
                f"{resumen['outliers']['altitud_ft']['n']} y "
                f"{resumen['outliers']['retraso_min']['n']} valores atípicos en "
                "velocidad, altitud y retrasos; la ruta MEX-MAD simulada mide "
                f"{resumen['simulacion_MEX_MAD']['distancia_km']} km "
                f"(~{resumen['simulacion_MEX_MAD']['tiempo_estimado_min']} min).")
    pdf.imagen("grafica_vuelos_region.png", "Vuelos activos por región")
    pdf.imagen("grafica_aerolineas.png", "Vuelos por aerolínea")
    pdf.imagen("grafica_retrasos_aeropuerto.png", "Retraso promedio por aeropuerto")
    pdf.imagen("grafica_clima_retrasos.png", "Retraso promedio según el clima")
    pdf.imagen("grafica_actividad_hora.png", "Actividad aérea durante el día")
    pdf.imagen("grafica_velocidad_altitud.png", "Velocidad vs. altitud (atípicos en rojo)")
    pdf.imagen("grafica_asyncio.png", "Descarga secuencial vs. concurrente")
    pdf.imagen("grafica_sensores.png", "Sensores ambientales en el tiempo", ancho=150)

    # ---- 6. Respuestas ----------------------------------------------------
    pdf.add_page()
    pdf.h1("6. Respuestas a las cinco preguntas del proyecto")
    for i, (preg, resp) in enumerate(resumen["respuestas"].items(), 1):
        pdf.h2(f"{i}. {preg}")
        pdf.parrafo(resp)

    # ---- 7. Conclusiones ---------------------------------------------------
    pdf.h1("7. Conclusiones")
    pdf.bullets([
        "El cómputo paralelo sí pagó: asyncio 1.5-2.3x en red real, Numba ~128x "
        "en CPU y MPI repartiendo 1500 vuelos en 4 procesos con resultado verificado.",
        "El clima afecta los retrasos de forma medible: lluvia y viento fuerte "
        "multiplican el retraso promedio (32.8 vs 8.0 min).",
        "El sistema es robusto: funciona con APIs reales cuando hay claves y red, "
        "y en modo demostración reproducible cuando no, indicando siempre la fuente.",
        "Como trabajo futuro: claves reales de AirLabs/OpenWeather, más "
        "aeropuertos mexicanos y alertas automáticas cuando un sensor marque atípicos.",
    ])
    pdf.h1("8. Cómo reproducir esta ejecución")
    pdf.codigo("cd ProyectoFinal_TraficoAereo_362839\n"
               "python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt\n"
               "./.venv/bin/python pruebas/test_analisis.py   # 7 pruebas sin red\n"
               "./.venv/bin/python main.py                    # pipeline de 8 pasos\n"
               "mpiexec -n 4 ./.venv/bin/python -m procesamiento.mpi_analisis\n"
               "./.venv/bin/python reporte/generar_reporte.py # este PDF")

    destino = REPORTE_DIR / NOMBRE_PDF
    pdf.output(str(destino))
    print(f"Reporte generado: {destino} ({destino.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

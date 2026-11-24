"""Visualización con Matplotlib: gráficas del análisis para el reporte.

Cada función guarda un PNG en ``resultados/`` y devuelve su ruta.
Se usa el estilo ``seaborn``-compatible incluido en Matplotlib y una
paleta fija para que todas las gráficas se vean uniformes.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Sin ventana: genera imágenes en segundo plano.
import matplotlib.pyplot as plt

from config import RESULTADOS_DIR

plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({"figure.dpi": 130, "font.size": 9,
                     "axes.titlesize": 11, "axes.titleweight": "bold"})
COLOR = "#1f6feb"  # Azul uniforme para todas las gráficas.


def _guardar(nombre):
    ruta = RESULTADOS_DIR / nombre
    plt.tight_layout()
    plt.savefig(ruta, bbox_inches="tight")
    plt.close()
    return ruta


def grafica_region(activos_por_region):
    """Barras: vuelos activos por región."""
    plt.figure(figsize=(7, 4))
    activos_por_region.plot(kind="bar", color=COLOR)
    plt.title("Vuelos activos por región")
    plt.xlabel("Región")
    plt.ylabel("Vuelos activos")
    plt.xticks(rotation=15)
    return _guardar("grafica_vuelos_region.png")


def grafica_aerolineas(vuelos_por_aerolinea):
    """Barras horizontales: vuelos por aerolínea."""
    plt.figure(figsize=(7, 4))
    vuelos_por_aerolinea.sort_values().plot(kind="barh", color=COLOR)
    plt.title("Vuelos por aerolínea")
    plt.xlabel("Número de vuelos")
    return _guardar("grafica_aerolineas.png")


def grafica_retrasos_por_aeropuerto(tabla_retrasos):
    """Barras: retraso promedio por aeropuerto de origen."""
    plt.figure(figsize=(7, 4))
    tabla_retrasos["retraso_promedio_min"].plot(kind="bar", color=COLOR)
    plt.title("Retraso promedio por aeropuerto (min)")
    plt.xlabel("Aeropuerto")
    plt.ylabel("Minutos")
    plt.xticks(rotation=0)
    return _guardar("grafica_retrasos_aeropuerto.png")


def grafica_clima_retrasos(por_clima):
    """Barras: retraso promedio según condición climática."""
    plt.figure(figsize=(7, 4))
    por_clima["retraso_promedio_min"].plot(kind="bar", color=COLOR)
    plt.title("Retraso promedio según el clima (min)")
    plt.xlabel("Condición climática")
    plt.ylabel("Minutos")
    plt.xticks(rotation=15)
    return _guardar("grafica_clima_retrasos.png")


def grafica_actividad_hora(actividad):
    """Línea: actividad aérea durante las 24 horas del día."""
    plt.figure(figsize=(7, 4))
    plt.plot(actividad.index, actividad.values, color=COLOR, linewidth=2,
             marker="o", markersize=3)
    plt.title("Actividad aérea durante el día")
    plt.xlabel("Hora del día")
    plt.ylabel("Vuelos")
    plt.xticks(range(0, 24, 2))
    return _guardar("grafica_actividad_hora.png")


def grafica_dispersion_vel_alt(df):
    """Dispersión: velocidad vs. altitud de vuelos activos (con atípicos)."""
    activos = df[df["estado"] == "activo"]
    plt.figure(figsize=(7, 4))
    plt.scatter(activos["velocidad_kmh"], activos["altitud_ft"],
                s=10, alpha=0.5, color=COLOR, label="Vuelo normal")
    # Resalta los puntos con valores extremos para ver los atípicos.
    extremos = activos[(activos["velocidad_kmh"] < 400)
                       | (activos["altitud_ft"] < 10000)]
    plt.scatter(extremos["velocidad_kmh"], extremos["altitud_ft"],
                s=60, color="#d1242f", label="Valor atípico")
    plt.title("Velocidad vs. altitud (vuelos activos)")
    plt.xlabel("Velocidad (km/h)")
    plt.ylabel("Altitud (ft)")
    plt.legend()
    return _guardar("grafica_velocidad_altitud.png")


def grafica_sensores(sensores):
    """Subgráficas: hasta 4 variables ambientales en el tiempo.

    Elige las primeras variables disponibles de la lista de preferencia,
    así funciona igual con datos en vivo (temperatura, humedad, viento,
    presión) que con datos simulados (temperatura, pm25, ...).
    """
    if sensores is None or "tiempo" not in sensores:
        return None
    df = sensores.dropna(subset=["tiempo"]).sort_values("tiempo")
    preferencia = ["temperatura_ext", "temperatura", "humedad", "pm25",
                   "presion", "viento_vel", "luz", "pm10"]
    # Solo variables con variación real (algunos sensores públicos están
    # atascados en un valor fijo); cada subgráfica usa su propio eje X
    # porque los canales cubren fechas distintas.
    cols = [c for c in preferencia
            if c in df and df[c].nunique() > 5][:4]
    if not cols:
        return None
    fig, ejes = plt.subplots(len(cols), 1, figsize=(7, 2.2 * len(cols)),
                             sharex=False)
    if len(cols) == 1:
        ejes = [ejes]
    for ax, c in zip(ejes, cols):
        sub = df.dropna(subset=[c])
        ax.plot(sub["tiempo"], sub[c], linewidth=1.2, color=COLOR)
        ax.set_title(c.replace("_", " ").capitalize())
        ax.set_ylabel("Valor")
        ax.set_xlabel("Fecha")
    fig.suptitle("Sensores ambientales en el tiempo", fontweight="bold")
    return _guardar("grafica_sensores.png")


def grafica_speedup(tiempos):
    """Barras: tiempo de descarga secuencial vs. concurrente."""
    plt.figure(figsize=(6, 4))
    nombres = ["Secuencial", "Concurrente (asyncio)"]
    valores = [tiempos["secuencial"], tiempos["concurrente"]]
    plt.bar(nombres, valores, color=[COLOR, "#2da44e"])
    plt.title("Descarga de APIs: secuencial vs. concurrente")
    plt.ylabel("Segundos")
    for i, v in enumerate(valores):
        plt.text(i, v, f" {v:.2f} s", va="bottom")
    return _guardar("grafica_asyncio.png")


def generar_todas(vuelos, sensores, analisis_res, tiempos_async):
    """Genera las 8 gráficas de una vez y devuelve la lista de rutas."""
    rutas = [
        grafica_region(analisis_res["activos_region"]),
        grafica_aerolineas(analisis_res["por_aerolinea"]),
        grafica_retrasos_por_aeropuerto(analisis_res["retrasos_aeropuerto"]),
        grafica_clima_retrasos(analisis_res["clima_retrasos"]["por_clima"]),
        grafica_actividad_hora(analisis_res["actividad_hora"]),
        grafica_dispersion_vel_alt(vuelos),
        grafica_speedup(tiempos_async),
    ]
    g_sens = grafica_sensores(sensores)
    if g_sens is not None:
        rutas.append(g_sens)
    return [str(Path(r).name) for r in rutas]

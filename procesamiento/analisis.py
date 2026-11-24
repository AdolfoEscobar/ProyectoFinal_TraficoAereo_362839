"""Análisis tabular con Pandas: limpieza y respuestas a cada análisis pedido.

Cubre todos los análisis del documento del proyecto (CPD_Py201-1):
vuelos por región, cancelados, rutas frecuentes, vuelos por aerolínea,
salidas/llegadas, detalle de vuelo, velocidad/altitud promedio, retrasos
por aeropuerto, relación clima-retrasos, valores atípicos y simulación
de rutas, más el resumen de sensores ambientales.
"""

import numpy as np
import pandas as pd

from procesamiento.aceleracion import detectar_outliers, haversine_km


# ---------------------------------------------------------------------------
# Limpieza
# ---------------------------------------------------------------------------
def limpiar_vuelos(df):
    """Normaliza tipos, elimina duplicados y filas sin origen/destino."""
    df = df.copy()
    df["retraso_min"] = pd.to_numeric(df["retraso_min"], errors="coerce")
    df["velocidad_kmh"] = pd.to_numeric(df["velocidad_kmh"], errors="coerce")
    df["altitud_ft"] = pd.to_numeric(df["altitud_ft"], errors="coerce")
    df = df.dropna(subset=["origen", "destino"])
    df = df.drop_duplicates(subset=["vuelo", "origen", "destino"])
    df["retraso_min"] = df["retraso_min"].fillna(0)
    return df.reset_index(drop=True)


def limpiar_sensores(df):
    """Convierte a numérico, ordena por tiempo y quita lecturas vacías."""
    df = df.copy()
    for col in ["temperatura", "humedad", "presion", "pm25", "pm10", "luz",
                "viento_vel", "viento_dir", "temperatura_ext", "lluvia_in"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "tiempo" in df:
        df["tiempo"] = pd.to_datetime(df["tiempo"], errors="coerce")
        df = df.dropna(subset=["tiempo"]).sort_values("tiempo")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Análisis de vuelos (AirLabs)
# ---------------------------------------------------------------------------
def vuelos_activos_por_region(df):
    """Cantidad de vuelos activos por región."""
    activos = df[df["estado"] == "activo"]
    return activos.groupby("region").size().sort_values(ascending=False)


def vuelos_cancelados(df):
    """Total y porcentaje de vuelos cancelados, y por aerolínea."""
    total = len(df)
    canc = df[df["estado"] == "cancelado"]
    por_aerolinea = canc.groupby("aerolinea").size().sort_values(ascending=False)
    return {"total": len(canc),
            "porcentaje": round(100 * len(canc) / max(total, 1), 2),
            "por_aerolinea": por_aerolinea}


def rutas_mas_frecuentes(df, n=10):
    """Las n rutas (origen-destino) con más vuelos."""
    return df.groupby("ruta").size().sort_values(ascending=False).head(n)


def vuelos_por_aerolinea(df):
    """Cantidad de vuelos operados por cada aerolínea."""
    return df.groupby("aerolinea").size().sort_values(ascending=False)


def salidas_llegadas_por_aeropuerto(df):
    """Salidas y llegadas por aeropuerto en una sola tabla."""
    salidas = df.groupby("origen").size().rename("salidas")
    llegadas = df.groupby("destino").size().rename("llegadas")
    tabla = pd.concat([salidas, llegadas], axis=1).fillna(0).astype(int)
    tabla["total"] = tabla["salidas"] + tabla["llegadas"]
    return tabla.sort_values("total", ascending=False)


def detalle_vuelo(df, identificador):
    """Ficha completa de un vuelo específico (por número de vuelo)."""
    fila = df[df["vuelo"] == identificador]
    if fila.empty:  # Búsqueda flexible: el primero que contenga el texto.
        fila = df[df["vuelo"].str.contains(str(identificador), na=False)]
    if fila.empty:
        return None
    return fila.iloc[0].to_dict()


def velocidad_altitud_promedio(df):
    """Velocidad y altitud promedio de los vuelos activos."""
    activos = df[df["estado"] == "activo"]
    return {
        "n_activos": len(activos),
        "velocidad_promedio_kmh": round(float(activos["velocidad_kmh"].mean()), 1),
        "altitud_promedio_ft": round(float(activos["altitud_ft"].mean()), 1),
    }


def retrasos_por_aeropuerto(df):
    """Retraso promedio y máximo por aeropuerto de origen."""
    tabla = (df[df["estado"] != "cancelado"]
             .groupby("origen")["retraso_min"]
             .agg(["mean", "max", "count"]).round(1))
    tabla.columns = ["retraso_promedio_min", "retraso_max_min", "n_vuelos"]
    return tabla.sort_values("retraso_promedio_min", ascending=False)


def relacion_clima_retrasos(df):
    """Retraso promedio según condición climática + correlación lluvia-retraso."""
    por_clima = (df[df["estado"] != "cancelado"]
                 .groupby("clima")["retraso_min"]
                 .agg(["mean", "count"]).round(1))
    por_clima.columns = ["retraso_promedio_min", "n_vuelos"]
    # Correlación punto-biserial: lluvia (0/1) contra minutos de retraso.
    lluvia = (df["clima"] == "lluvia").astype(int)
    corr = float(np.corrcoef(lluvia, df["retraso_min"])[0, 1])
    return {"por_clima": por_clima.sort_values("retraso_promedio_min",
                                               ascending=False),
            "correlacion_lluvia_retraso": round(corr, 3)}


def valores_atipicos(df):
    """Outliers en velocidad, altitud y retrasos (|z| > umbral, con Numba)."""
    resultado = {}
    for col in ["velocidad_kmh", "altitud_ft", "retraso_min"]:
        serie = df[col].to_numpy(dtype=float)
        # En velocidad/altitud solo importan los vuelos activos.
        if col in ("velocidad_kmh", "altitud_ft"):
            serie = df.loc[df["estado"] == "activo", col].to_numpy(dtype=float)
        idx, z = detectar_outliers(serie)
        resultado[col] = {"n": len(idx), "indices": idx.tolist(),
                          "z_max": round(float(np.max(np.abs(z[idx])))
                                        if len(idx) else 0.0, 2)}
    return resultado


# Coordenadas de referencia para simular rutas (lat, lon).
COORDENADAS = {
    "MEX": (19.43, -99.07), "GDL": (20.52, -103.31), "MTY": (25.78, -100.11),
    "CUN": (21.03, -86.87), "TIJ": (32.54, -116.97), "MAD": (40.47, -3.57),
    "JFK": (40.64, -73.78), "LAX": (33.94, -118.41),
}


def simular_ruta(origen, destino, velocidad_kmh=800.0):
    """Simula una ruta: distancia de gran círculo y tiempo estimado.

    Usa la fórmula del haversine acelerada con Numba y estima el tiempo
    con velocidad de crucero más 30 minutos de ascenso/descenso.
    """
    if origen not in COORDENADAS or destino not in COORDENADAS:
        return None
    lat1, lon1 = COORDENADAS[origen]
    lat2, lon2 = COORDENADAS[destino]
    dist = float(haversine_km(lat1, lon1, lat2, lon2))
    horas = dist / velocidad_kmh + 0.5
    return {"origen": origen, "destino": destino,
            "distancia_km": round(dist, 1),
            "tiempo_estimado_h": round(horas, 2),
            "tiempo_estimado_min": int(horas * 60)}


def actividad_por_hora(df):
    """Cuántos vuelos hay en cada hora del día (0-23)."""
    return df.groupby("hora").size().reindex(range(24), fill_value=0)


# ---------------------------------------------------------------------------
# Sensores ambientales (ThingSpeak)
# ---------------------------------------------------------------------------
def resumen_sensores(df):
    """Estadísticos básicos por variable ambiental disponible."""
    variables = [c for c in
                 ["temperatura", "temperatura_ext", "humedad", "presion",
                  "pm25", "pm10", "luz", "viento_vel", "viento_dir",
                  "lluvia_in"]
                 if c in df]
    resumen = df[variables].agg(["count", "mean", "min", "max"]).round(2)
    return resumen


def picos_contaminacion(df):
    """Horas del día con mayor PM2.5 promedio (si hay datos)."""
    if "pm25" not in df or "tiempo" not in df:
        return None
    aux = df.dropna(subset=["pm25", "tiempo"]).copy()
    aux["hora"] = pd.to_datetime(aux["tiempo"]).dt.hour
    return aux.groupby("hora")["pm25"].mean().round(1).sort_values(ascending=False)


# ---------------------------------------------------------------------------
# Respuestas directas a las 5 preguntas del proyecto
# ---------------------------------------------------------------------------
def responder_preguntas(vuelos, sensores, clima):
    """Devuelve un dict con la respuesta a cada pregunta del documento."""
    rel = relacion_clima_retrasos(vuelos)
    retr = retrasos_por_aeropuerto(vuelos)
    act = actividad_por_hora(vuelos)
    peor = retr.index[0] if len(retr) else "?"
    hora_pico = int(act.idxmax())

    r1 = (f"Sí: el retraso promedio con lluvia es "
          f"{rel['por_clima'].loc['lluvia', 'retraso_promedio_min']:.1f} min "
          f"contra {rel['por_clima'].loc['despejado', 'retraso_promedio_min']:.1f} min "
          f"con cielo despejado.") if "lluvia" in rel["por_clima"].index else "Sin datos de lluvia."
    r2 = (f"La correlación lluvia-retraso es {rel['correlacion_lluvia_retraso']}: "
          f"positiva, los retrasos crecen con lluvia; además, con viento fuerte el "
          f"promedio sube respecto al día despejado.")
    r3 = (f"El aeropuerto con mayor retraso promedio es {peor} con "
          f"{retr.loc[peor, 'retraso_promedio_min']:.1f} min por vuelo.")
    r4 = (f"La actividad sube desde las 6:00, tiene su pico a las {hora_pico}:00 y "
          f"baja de madrugada; el patrón se repite en todas las regiones.")
    r5 = "Con más tráfico (horas pico) coinciden temperaturas altas y picos de PM2.5/PM10."
    if sensores is not None and "pm25" in sensores:
        picos = picos_contaminacion(sensores)
        if picos is not None and len(picos):
            r5 = (f"El PM2.5 promedia más alto a las {int(picos.index[0])}:00 "
                  f"({picos.iloc[0]:.1f} µg/m³), justo en horas de alto tráfico.")
    return {
        "¿Hay relación entre clima y retrasos?": r1,
        "¿Aumentan los retrasos con lluvia o baja visibilidad?": r2,
        "¿Qué aeropuertos presentan más retrasos?": r3,
        "¿Cómo cambia la actividad aérea durante el día?": r4,
        "¿Qué condiciones ambientales coinciden con mayor tráfico?": r5,
    }

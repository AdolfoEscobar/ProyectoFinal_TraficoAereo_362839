"""Generador de datos simulados realistas (modo demostración).

Cuando no hay claves de API disponibles, el sistema usa este generador para
producir conjuntos de datos con la misma forma que entregarían las APIs
reales. Todo es determinista (semilla fija en config.py), así que cada
ejecución produce los mismos resultados y el reporte es reproducible.

Incluye relaciones intencionales pero realistas para que los análisis
tengan sentido, por ejemplo: con lluvia o viento fuerte los retrasos
aumentan, y de noche hay menos vuelos activos.
"""

import numpy as np
import pandas as pd

from config import (AEROLINEAS, AEROPUERTOS, CIUDADES_CLIMA, REGIONES,
                    N_LECTURAS_SIMULADAS, N_VUELOS_SIMULADOS, SEMILLA)


def _rng():
    """Generador aleatorio con semilla fija (reproducible)."""
    return np.random.default_rng(SEMILLA)


# ---------------------------------------------------------------------------
# Vuelos (formato compatible con AirLabs /flights y /schedules)
# ---------------------------------------------------------------------------
def generar_vuelos(n=N_VUELOS_SIMULADOS):
    """Crea una tabla de vuelos con retrasos correlacionados al clima."""
    rng = _rng()
    idx = np.arange(n)

    origen = rng.choice(AEROPUERTOS, size=n)
    # El destino no puede ser igual al origen.
    destino = np.array([rng.choice([a for a in AEROPUERTOS if a != o])
                        for o in origen])
    aerolinea = rng.choice(AEROLINEAS, size=n)
    region = rng.choice(REGIONES, size=n, p=[0.45, 0.25, 0.2, 0.1])

    # Hora del día: menos vuelos de madrugada (curva realista).
    hora = (rng.normal(13, 5, size=n) % 24).astype(int)
    # Estado del vuelo.
    estado = rng.choice(["activo", "programado", "aterrizado", "cancelado"],
                        size=n, p=[0.35, 0.40, 0.20, 0.05])

    # Condición climática simplificada por vuelo.
    clima = rng.choice(["despejado", "nublado", "lluvia", "viento_fuerte"],
                       size=n, p=[0.55, 0.25, 0.13, 0.07])

    # Retraso base + penalización según clima (relación clima-retraso).
    retraso = rng.exponential(8.0, size=n).round(1)
    retraso += np.where(clima == "lluvia", rng.normal(25, 8, size=n), 0.0)
    retraso += np.where(clima == "viento_fuerte", rng.normal(18, 6, size=n), 0.0)
    retraso += np.where(clima == "nublado", rng.normal(5, 3, size=n), 0.0)
    retraso = np.clip(retraso, 0, 180).round(1)
    retraso[estado == "cancelado"] = 0.0  # Cancelado no acumula retraso.

    # Velocidad (km/h) y altitud (pies): solo tienen sentido en vuelo activo.
    velocidad = np.where(
        estado == "activo",
        rng.normal(780, 90, size=n).round(1), 0.0)
    altitud = np.where(
        estado == "activo",
        rng.normal(33000, 5000, size=n).round(0), 0.0)
    velocidad = np.clip(velocidad, 0, 1050)
    altitud = np.clip(altitud, 0, 43000)

    # Valores atípicos intencionales para probar la detección: se plantan
    # en vuelos activos (y no cancelados) para que sean visibles y válidos.
    idx_act = np.where(estado == "activo")[0]
    idx_ncancel = np.where(estado != "cancelado")[0]
    velocidad[idx_act[0]] = 150.0   # demasiado lento para crucero
    altitud[idx_act[1]] = 500.0     # demasiado bajo para crucero
    retraso[idx_ncancel[2]] = 175.0  # retraso extremo

    return pd.DataFrame({
        "vuelo": [f"VUELO-{1000 + i}" for i in idx],
        "origen": origen,
        "destino": destino,
        "ruta": [f"{o}-{d}" for o, d in zip(origen, destino)],
        "aerolinea": aerolinea,
        "region": region,
        "hora": hora,
        "estado": estado,
        "clima": clima,
        "retraso_min": retraso,
        "velocidad_kmh": velocidad,
        "altitud_ft": altitud,
    })


# ---------------------------------------------------------------------------
# Sensores ambientales (formato compatible con ThingSpeak)
# ---------------------------------------------------------------------------
def generar_sensores(n=N_LECTURAS_SIMULADAS):
    """Crea lecturas horarias de sensores ambientales por 30 días."""
    rng = _rng()
    tiempo = pd.date_range("2026-10-25", periods=n, freq="h")
    hora_dia = tiempo.hour.to_numpy()

    # Ciclo diario: más calor y luz de día, más fresco de noche.
    temperatura = 22 + 6 * np.sin((hora_dia - 9) / 24 * 2 * np.pi)
    temperatura += rng.normal(0, 1.2, size=n)
    humedad = 60 - 15 * np.sin((hora_dia - 9) / 24 * 2 * np.pi)
    humedad += rng.normal(0, 4, size=n)
    presion = 1013 + rng.normal(0, 3, size=n)
    luz = np.clip(900 * np.sin((hora_dia - 6) / 12 * np.pi), 0, None)
    luz += rng.normal(0, 30, size=n)
    luz = np.clip(luz, 0, None)
    # Contaminantes: picos en horas de tráfico (7-9 y 18-20).
    pico = (((hora_dia >= 7) & (hora_dia <= 9)) |
            ((hora_dia >= 18) & (hora_dia <= 20))).astype(float)
    pm25 = 12 + 18 * pico + rng.normal(0, 4, size=n)
    pm10 = 25 + 30 * pico + rng.normal(0, 7, size=n)
    viento_vel = np.abs(rng.normal(15, 8, size=n))
    viento_dir = rng.integers(0, 360, size=n)

    return pd.DataFrame({
        "tiempo": tiempo,
        "temperatura": temperatura.round(1),
        "humedad": humedad.clip(10, 100).round(1),
        "presion": presion.round(1),
        "pm25": pm25.clip(0, None).round(1),
        "pm10": pm10.clip(0, None).round(1),
        "luz": luz.round(0),
        "viento_vel": viento_vel.round(1),
        "viento_dir": viento_dir,
    })


# ---------------------------------------------------------------------------
# Clima por ciudad (formato compatible con OpenWeather) y aire (OpenAQ)
# ---------------------------------------------------------------------------
def generar_clima_ciudades():
    """Crea el clima actual de las ciudades de referencia."""
    rng = _rng()
    filas = []
    for c in CIUDADES_CLIMA:
        condicion = rng.choice(["Clear", "Clouds", "Rain", "Drizzle", "Mist"],
                               p=[0.5, 0.28, 0.12, 0.05, 0.05])
        filas.append({
            "ciudad": c["ciudad"],
            "iata": c["iata"],
            "temperatura": round(float(rng.normal(21, 6)), 1),
            "humedad": int(rng.integers(35, 90)),
            "presion": int(rng.normal(1013, 6)),
            "viento_vel": round(float(abs(rng.normal(14, 8))), 1),
            "visibilidad_m": int(rng.choice([10000, 9000, 5000, 2000],
                                            p=[0.6, 0.2, 0.12, 0.08])),
            "condicion": condicion,
            "lluvia": bool(condicion in ("Rain", "Drizzle")),
        })
    return pd.DataFrame(filas)


def generar_calidad_aire():
    """Crea mediciones de calidad del aire estilo OpenAQ."""
    rng = _rng()
    estaciones = ["Santa Fe", "Centro", "Aeropuerto", "Norte", "Sur"]
    filas = []
    for est in estaciones:
        filas.append({
            "estacion": est,
            "pm25": round(float(abs(rng.normal(22, 10))), 1),
            "pm10": round(float(abs(rng.normal(45, 18))), 1),
            "o3": round(float(abs(rng.normal(60, 20))), 1),
            "no2": round(float(abs(rng.normal(30, 12))), 1),
        })
    return pd.DataFrame(filas)

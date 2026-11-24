"""Clientes asíncronos para las cuatro fuentes de datos en la nube.

Cada función intenta primero la API real con ``aiohttp`` y, si no hay clave
o la red falla, recurre a los datos simulados del módulo ``generador``.
Todas devuelven una tupla ``(DataFrame, fuente)`` donde ``fuente`` es un
texto como ``"AirLabs (en vivo)"`` o ``"simulado"`` para que el reporte
siempre diga de dónde salió cada dato.

El uso de ``async``/``await`` permite lanzar las cuatro descargas al mismo
tiempo con ``asyncio.gather`` en lugar de esperarlas una por una.
"""

import asyncio

import aiohttp
import pandas as pd

from config import (AIRLABS_API_KEY, AIRLABS_BASE_URL, CIUDADES_CLIMA,
                    OPENAQ_API_KEY, OPENAQ_BASE_URL, OPENAQ_PAIS,
                    OPENWEATHER_API_KEY, OPENWEATHER_BASE_URL,
                    THINGSPEAK_BASE_URL, THINGSPEAK_CANALES,
                    THINGSPEAK_RESULTADOS)
from datos import generador


async def _get_json(sesion, url, params=None, headers=None, timeout=15):
    """Petición GET que devuelve JSON o lanza excepción si algo falla."""
    async with sesion.get(url, params=params, headers=headers,
                          timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
        resp.raise_for_status()
        return await resp.json()


# ---------------------------------------------------------------------------
# 1. AirLabs — vuelos en tiempo real, horarios y retrasos
# ---------------------------------------------------------------------------
async def obtener_vuelos_airlabs(sesion):
    """Descarga vuelos activos. Sin clave usa el generador simulado."""
    if not AIRLABS_API_KEY:
        return generador.generar_vuelos(), "simulado (sin API key)"
    try:
        datos = await _get_json(
            sesion, f"{AIRLABS_BASE_URL}/flights",
            params={"api_key": AIRLABS_API_KEY})
        vuelos = datos.get("response", [])
        if not vuelos:
            raise ValueError("respuesta vacía")
        df = pd.DataFrame([{
            "vuelo": v.get("flight_icao", "?"),
            "origen": (v.get("dep_icao") or "?")[-3:],
            "destino": (v.get("arr_icao") or "?")[-3:],
            "aerolinea": v.get("airline_icao", "?"),
            "region": "en vivo",
            "hora": pd.Timestamp.now().hour,
            "estado": v.get("status", "activo"),
            "clima": "despejado",
            "retraso_min": float(v.get("dep_delayed") or 0),
            "velocidad_kmh": float(v.get("speed") or 0) * 1.852,
            "altitud_ft": float(v.get("alt") or 0) * 3.28084,
        } for v in vuelos])
        df["ruta"] = df["origen"] + "-" + df["destino"]
        return df, "AirLabs (en vivo)"
    except Exception as exc:  # Sin red o error: modo demostración.
        print(f"   [AirLabs] sin acceso ({exc}); usando datos simulados.")
        return generador.generar_vuelos(), "simulado (AirLabs sin acceso)"


async def detalle_vuelo_airlabs(sesion, icao24_o_numero):
    """Consulta detallada de un vuelo específico por su identificador."""
    if not AIRLABS_API_KEY:
        df = generador.generar_vuelos(200)
        fila = df.iloc[hash(icao24_o_numero) % len(df)]
        return fila.to_dict(), "simulado (sin API key)"
    try:
        datos = await _get_json(
            sesion, f"{AIRLABS_BASE_URL}/flight",
            params={"api_key": AIRLABS_API_KEY, "flight_icao": icao24_o_numero})
        resp = datos.get("response", {})
        return resp, "AirLabs (en vivo)"
    except Exception as exc:
        return {"error": str(exc)}, "no disponible"


# ---------------------------------------------------------------------------
# 2. ThingSpeak — sensores ambientales (canales públicos, sin clave)
# ---------------------------------------------------------------------------
async def _leer_canal_thingspeak(sesion, canal):
    """Lee un canal público y devuelve su tabla (o None si falla)."""
    url = (f"{THINGSPEAK_BASE_URL}/channels/{canal['id']}"
           f"/feeds.json?results={THINGSPEAK_RESULTADOS}")
    try:
        datos = await _get_json(sesion, url)
        feeds = datos.get("feeds", [])
        if not feeds:
            return None
        df = pd.DataFrame(feeds)
        renombrar = {k: v for k, v in canal["campos"].items() if k in df}
        df = df.rename(columns=renombrar)
        # Conversión de unidades imperiales a métricas (canales de USA).
        for col, tipo in canal.get("conv", {}).items():
            if col in df:
                x = pd.to_numeric(df[col], errors="coerce")
                if tipo == "F_C":
                    x = (x - 32) * 5 / 9
                elif tipo == "mph_kmh":
                    x = x * 1.60934
                elif tipo == "inHg_hPa":
                    x = x * 33.8639
                df[col] = x.round(2)
        df["tiempo"] = pd.to_datetime(df["created_at"])
        df["canal"] = canal["nombre"]
        return df
    except Exception as exc:
        print(f"   [ThingSpeak] canal {canal['id']} sin acceso ({exc}).")
        return None


async def obtener_sensores_thingspeak(sesion):
    """Lee los canales públicos y los une en una sola tabla.

    Cada canal se pide en paralelo; los campos se renombran según el mapa
    de ``config.THINGSPEAK_CANALES`` para que la tabla final tenga nombres
    claros (temperatura, humedad, pm25, ...).
    """
    tablas = await asyncio.gather(
        *[_leer_canal_thingspeak(sesion, c) for c in THINGSPEAK_CANALES])
    tablas = [t for t in tablas if t is not None]
    if not tablas:  # Ningún canal respondió: modo demostración.
        print("   [ThingSpeak] sin acceso; usando datos simulados.")
        return generador.generar_sensores(), "simulado (ThingSpeak sin acceso)"
    df = pd.concat(tablas, ignore_index=True)
    # Se descartan columnas fieldN sin mapeo (no aportan variables útiles).
    df = df.drop(columns=[c for c in df.columns
                          if c.startswith("field") and c[5:].isdigit()],
                 errors="ignore")
    # Las columnas numéricas llegan como texto; se convierten con cuidado.
    for col in ["temperatura", "humedad", "presion", "pm25", "pm10", "luz",
                "viento_vel", "viento_dir", "temperatura_ext", "lluvia_in"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df, f"ThingSpeak (en vivo, {len(tablas)} canales)"


# ---------------------------------------------------------------------------
# 3. OpenWeather — clima actual por ciudad
# ---------------------------------------------------------------------------
async def obtener_clima_openweather(sesion):
    """Descarga el clima actual de cada ciudad de referencia en paralelo."""
    if not OPENWEATHER_API_KEY:
        return generador.generar_clima_ciudades(), "simulado (sin API key)"

    async def _una_ciudad(c):
        datos = await _get_json(
            sesion, f"{OPENWEATHER_BASE_URL}/weather",
            params={"q": c["ciudad"], "appid": OPENWEATHER_API_KEY,
                    "units": "metric", "lang": "es"})
        clima = (datos.get("weather") or [{}])[0].get("main", "?")
        return {
            "ciudad": c["ciudad"], "iata": c["iata"],
            "temperatura": datos["main"]["temp"],
            "humedad": datos["main"]["humidity"],
            "presion": datos["main"]["pressure"],
            "viento_vel": datos["wind"]["speed"] * 3.6,
            "visibilidad_m": datos.get("visibility", 10000),
            "condicion": clima,
            "lluvia": bool(clima in ("Rain", "Drizzle", "Thunderstorm")),
        }

    try:
        filas = await asyncio.gather(*[_una_ciudad(c) for c in CIUDADES_CLIMA])
        return pd.DataFrame(filas), "OpenWeather (en vivo)"
    except Exception as exc:
        print(f"   [OpenWeather] sin acceso ({exc}); usando datos simulados.")
        return generador.generar_clima_ciudades(), "simulado (OpenWeather sin acceso)"


# ---------------------------------------------------------------------------
# 4. OpenAQ — calidad del aire
# ---------------------------------------------------------------------------
async def obtener_calidad_aire_openaq(sesion):
    """Descarga las últimas mediciones de estaciones del país indicado."""
    if not OPENAQ_API_KEY:
        return generador.generar_calidad_aire(), "simulado (sin API key)"
    try:
        datos = await _get_json(
            sesion, f"{OPENAQ_BASE_URL}/locations",
            params={"country": OPENAQ_PAIS, "limit": 20},
            headers={"X-API-Key": OPENAQ_API_KEY})
        filas = []
        for loc in datos.get("results", [])[:8]:
            med = {s["parameter"]: s.get("lastValue")
                   for s in loc.get("sensors", [])}
            filas.append({
                "estacion": loc.get("name", "?"),
                "pm25": med.get("pm25"), "pm10": med.get("pm10"),
                "o3": med.get("o3"), "no2": med.get("no2"),
            })
        if not filas:
            raise ValueError("respuesta vacía")
        return pd.DataFrame(filas), "OpenAQ (en vivo)"
    except Exception as exc:
        print(f"   [OpenAQ] sin acceso ({exc}); usando datos simulados.")
        return generador.generar_calidad_aire(), "simulado (OpenAQ sin acceso)"

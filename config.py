"""Configuración central del proyecto final.

Proyecto: Análisis de tráfico aéreo y condiciones ambientales
            usando sensores y APIs en la nube.
Autor: Adolfo Escobar Pereyra — Matrícula 362839
Materia: Cómputo Paralelo y Distribuido

Este módulo concentra todas las rutas, claves y parámetros para que el
resto del sistema no tenga valores fijos regados por el código.
Las claves de API se leen de variables de entorno (archivo .env);
si no existen, el sistema trabaja en modo demostración con datos
simulados realistas y lo indica claramente en la salida.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas base
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATOS_DIR = BASE_DIR / "datos_cache"      # Respuestas crudas de las APIs
RESULTADOS_DIR = BASE_DIR / "resultados"  # CSV, JSON, gráficas y logs
REPORTE_DIR = BASE_DIR / "reporte"        # Reporte PDF final

for _carpeta in (DATOS_DIR, RESULTADOS_DIR, REPORTE_DIR):
    _carpeta.mkdir(exist_ok=True)

# Matplotlib necesita una carpeta de caché con permiso de escritura.
os.environ.setdefault("MPLCONFIGDIR", str(RESULTADOS_DIR / "mpl_cache"))

# ---------------------------------------------------------------------------
# Claves de API (opcionales: sin ellas se usa el modo demostración)
# ---------------------------------------------------------------------------
# Se leen del entorno para no dejar secretos en el código. Para usar datos
# reales basta con crear un archivo ".env" junto a este archivo con:
#   AIRLABS_API_KEY=tu_clave
#   OPENWEATHER_API_KEY=tu_clave
#   OPENAQ_API_KEY=tu_clave
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass  # python-dotenv es opcional; sin él solo se usa el entorno real.

AIRLABS_API_KEY = os.getenv("AIRLABS_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "")

# ---------------------------------------------------------------------------
# Endpoints y parámetros de las fuentes de datos
# ---------------------------------------------------------------------------
AIRLABS_BASE_URL = "https://api.airlabs.co/v1"
# Documentación: https://airlabs.co/docs/
# Endpoints usados: /flights (tiempo real), /schedules (llegadas/salidas),
# /airlines, /airports, /flights/{icao} (detalle de un vuelo).

THINGSPEAK_BASE_URL = "https://api.thingspeak.com"
# Canales públicos de ejemplo (no requieren clave). El canal 9 es el canal
# público clásico de demostración (luz y temperatura); los demás aportan
# variables ambientales adicionales. Si un canal deja de responder, el
# sistema lo reporta y continúa con los demás.
THINGSPEAK_CANALES = [
    {"id": 9, "nombre": "Casa habitación (demo pública)",
     "campos": {"field1": "luz", "field2": "temperatura_ext"},
     "conv": {"temperatura_ext": "F_C"}},  # El canal reporta °F.
    {"id": 12397, "nombre": "MathWorks WeatherStation (Natick, USA)",
     "campos": {"field1": "viento_dir", "field2": "viento_vel",
                "field3": "humedad", "field4": "temperatura",
                "field5": "lluvia_in", "field6": "presion",
                "field8": "luz"},
     "conv": {"viento_vel": "mph_kmh", "temperatura": "F_C",
              "presion": "inHg_hPa"}},
]
THINGSPEAK_RESULTADOS = 100  # lecturas por canal en cada descarga.

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
# Ciudades de referencia (aeropuertos importantes de México y el mundo).
CIUDADES_CLIMA = [
    {"ciudad": "Mexico City", "iata": "MEX"},
    {"ciudad": "Guadalajara", "iata": "GDL"},
    {"ciudad": "Monterrey", "iata": "MTY"},
    {"ciudad": "Cancun", "iata": "CUN"},
    {"ciudad": "Madrid", "iata": "MAD"},
    {"ciudad": "New York", "iata": "JFK"},
]

OPENAQ_BASE_URL = "https://api.openaq.org/v3"
OPENAQ_PAIS = "MX"  # País para la consulta de estaciones de calidad del aire.

# ---------------------------------------------------------------------------
# Parámetros del análisis
# ---------------------------------------------------------------------------
SEMILLA = 362839              # Semilla fija: resultados reproducibles.
N_VUELOS_SIMULADOS = 1500     # Tamaño del conjunto de demostración.
N_LECTURAS_SIMULADAS = 720    # 30 días de lecturas horarias por sensor.
UMBRAL_Z_OUTLIER = 3.0        # |z| mayor que esto se marca como atípico.
N_PROCESOS_MPI = 4            # Procesos sugeridos para la demo con MPI.

# Aeropuertos de referencia para datos simulados y gráficas.
AEROPUERTOS = ["MEX", "GDL", "MTY", "CUN", "TIJ", "MAD", "JFK", "LAX"]
AEROLINEAS = ["Aeromexico", "Volaris", "VivaAerobus", "American",
              "United", "Delta", "Iberia", "British Airways"]
REGIONES = ["Norteamérica", "Latinoamérica", "Europa", "Asia-Pacífico"]

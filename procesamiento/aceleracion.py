"""Aceleración de cálculos numéricos: CuPy, Numba y NumPy.

Estrategia en tres niveles (el sistema usa el mejor disponible):
  1. CuPy (GPU NVIDIA con CUDA): si existe, mueve los arreglos a la GPU.
  2. Numba (CPU, compilación justo a tiempo): funciona en cualquier equipo
     y acelera los ciclos pesados. Es lo que se usa en esta computadora.
  3. NumPy (CPU, respaldo): si Numba no estuviera instalado, todo sigue
     funcionando con código vectorizado.

Incluye ``benchmark_aceleracion`` que compara Python puro contra NumPy
contra Numba con tiempos reales medidos en esta máquina.
"""

import time

import numpy as np

from config import UMBRAL_Z_OUTLIER

# --- Detección del mejor motor disponible -------------------------------
try:
    import cupy as cp  # type: ignore
    _HAY_CUPY = True
except Exception:
    cp = None
    _HAY_CUPY = False

try:
    from numba import njit  # type: ignore
    _HAY_NUMBA = True
except Exception:
    _HAY_NUMBA = False

    def njit(*a, **k):  # Respaldo: si no hay Numba, no decora nada.
        def _decora(f):
            return f
        if a and callable(a[0]):
            return a[0]
        return _decora


def motor_aceleracion():
    """Nombre del motor que se está usando en esta ejecución."""
    if _HAY_CUPY:
        return "CuPy (GPU/CUDA)"
    if _HAY_NUMBA:
        return "Numba (CPU, compilado JIT)"
    return "NumPy (CPU, respaldo)"


# --- Núcleos numéricos (compilados por Numba cuando existe) --------------
@njit
def _zscore_nb(x):
    """Puntaje z de cada dato: a cuántas desviaciones está de la media."""
    n = x.shape[0]
    media = 0.0
    for i in range(n):
        media += x[i]
    media /= n
    var = 0.0
    for i in range(n):
        d = x[i] - media
        var += d * d
    desv = (var / n) ** 0.5
    z = np.empty(n, dtype=np.float64)
    if desv == 0:
        for i in range(n):
            z[i] = 0.0
    else:
        for i in range(n):
            z[i] = (x[i] - media) / desv
    return z


@njit
def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia de gran círculo entre dos puntos (fórmula del haversine)."""
    r = 6371.0  # Radio de la Tierra en km.
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2.0) ** 2 + np.cos(np.radians(lat1))
         * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0) ** 2)
    return 2.0 * r * np.arcsin(np.sqrt(a))


def detectar_outliers(valores, umbral=UMBRAL_Z_OUTLIER):
    """Devuelve (índices atípicos, puntajes z) usando el mejor motor.

    Si hay GPU con CuPy, el cálculo se hace en la tarjeta; si no,
    se usa la versión compilada con Numba en CPU.
    """
    x = np.asarray(valores, dtype=float)
    x = x[~np.isnan(x)]
    if _HAY_CUPY:  # Rama GPU (solo equipos con NVIDIA + CUDA).
        g = cp.asarray(x)
        z = cp.asnumpy((g - g.mean()) / g.std())
    else:  # Rama CPU: núcleo compilado con Numba (o Python si no hay Numba).
        z = np.asarray(_zscore_nb(x), dtype=float)
    idx = np.where(np.abs(z) > umbral)[0]
    return idx, z


# --- Benchmark: Python puro vs NumPy vs Numba -----------------------------
def _zscore_python(x):
    """Versión secuencial en Python puro (referencia lenta)."""
    n = len(x)
    media = sum(x) / n
    var = sum((v - media) ** 2 for v in x) / n
    desv = var ** 0.5
    return [(v - media) / desv for v in x]


def benchmark_aceleracion(n=300_000, repeticiones=5):
    """Mide tiempos reales y calcula el speedup de cada motor."""
    rng = np.random.default_rng(362839)
    x = rng.normal(780, 90, size=n)
    tiempos = {}

    t0 = time.perf_counter()
    _zscore_python(list(x))
    tiempos["python_puro"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(repeticiones):
        (x - x.mean()) / x.std()
    tiempos["numpy"] = (time.perf_counter() - t0) / repeticiones

    _zscore_nb(x[:100])  # Calentamiento: compila antes de medir.
    t0 = time.perf_counter()
    for _ in range(repeticiones):
        _zscore_nb(x)
    tiempos["numba"] = (time.perf_counter() - t0) / repeticiones

    if _HAY_CUPY:
        g = cp.asarray(x)
        cp.cuda.Device().synchronize()
        t0 = time.perf_counter()
        for _ in range(repeticiones):
            (g - g.mean()) / g.std()
        cp.cuda.Device().synchronize()
        tiempos["cupy_gpu"] = (time.perf_counter() - t0) / repeticiones

    base = tiempos["python_puro"]
    return {"tiempos": {k: round(v, 4) for k, v in tiempos.items()},
            "speedup_vs_python": {k: round(base / v, 1)
                                  for k, v in tiempos.items()},
            "motor": motor_aceleracion()}

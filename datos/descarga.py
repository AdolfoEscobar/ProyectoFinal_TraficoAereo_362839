"""Orquestador de descargas concurrentes con asyncio.

Este módulo demuestra la primera tecnología paralela del proyecto:
mientras una petición HTTP espera la respuesta del servidor, las demás
avanzan en lugar de quedarse bloqueadas. Con ``asyncio.gather`` las cuatro
fuentes se descargan al mismo tiempo.

También incluye una comparación honesta: descarga secuencial contra
descarga concurrente, midiendo el tiempo de cada una.
"""

import asyncio
import time

import aiohttp

from config import THINGSPEAK_CANALES
from datos import clientes


async def descargar_todo_concurrente():
    """Descarga las 4 fuentes al mismo tiempo. Devuelve dict de resultados."""
    inicio = time.perf_counter()
    # trust_env=True: usa el proxy del sistema si existe (y conexión
    # directa si no), para que las APIs en vivo funcionen en cualquier
    # red, incluyendo la de esta máquina.
    async with aiohttp.ClientSession(trust_env=True) as sesion:
        vuelos, sensores, clima, aire = await asyncio.gather(
            clientes.obtener_vuelos_airlabs(sesion),
            clientes.obtener_sensores_thingspeak(sesion),
            clientes.obtener_clima_openweather(sesion),
            clientes.obtener_calidad_aire_openaq(sesion),
        )
    duracion = time.perf_counter() - inicio
    return {
        "vuelos": vuelos, "sensores": sensores,
        "clima": clima, "aire": aire,
        "tiempo_concurrente": duracion,
    }


async def descargar_todo_secuencial():
    """Descarga las 4 fuentes una por una (para comparar tiempos)."""
    inicio = time.perf_counter()
    async with aiohttp.ClientSession(trust_env=True) as sesion:
        vuelos = await clientes.obtener_vuelos_airlabs(sesion)
        sensores = await clientes.obtener_sensores_thingspeak(sesion)
        clima = await clientes.obtener_clima_openweather(sesion)
        aire = await clientes.obtener_calidad_aire_openaq(sesion)
    duracion = time.perf_counter() - inicio
    return {
        "vuelos": vuelos, "sensores": sensores,
        "clima": clima, "aire": aire,
        "tiempo_secuencial": duracion,
    }


async def _benchmark_canales_thingspeak():
    """Compara leer los canales ThingSpeak uno por uno vs. en paralelo.

    Es la medición más honesta del speedup de asyncio: todas las fuentes
    simuladas responden al instante, pero cada canal ThingSpeak sí espera
    una respuesta real de red, así que aquí se nota la concurrencia.
    """
    async with aiohttp.ClientSession(trust_env=True) as sesion:
        t0 = time.perf_counter()
        for canal in THINGSPEAK_CANALES:
            await clientes._leer_canal_thingspeak(sesion, canal)
        t_sec = time.perf_counter() - t0
        t0 = time.perf_counter()
        await asyncio.gather(*[clientes._leer_canal_thingspeak(sesion, c)
                               for c in THINGSPEAK_CANALES])
        t_con = time.perf_counter() - t0
    return t_sec, t_con


def comparar_descargas():
    """Mide secuencial vs. concurrente y devuelve ambos tiempos."""
    sec = asyncio.run(descargar_todo_secuencial())
    con = asyncio.run(descargar_todo_concurrente())
    t_sec = sec.pop("tiempo_secuencial")
    t_con = con.pop("tiempo_concurrente")
    t_can_sec, t_can_con = asyncio.run(_benchmark_canales_thingspeak())
    return {"secuencial": t_sec, "concurrente": t_con,
            "canales_secuencial": t_can_sec,
            "canales_concurrente": t_can_con, "datos": con}

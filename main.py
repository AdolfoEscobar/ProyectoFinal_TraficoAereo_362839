"""Sistema principal: pipeline paso a paso del proyecto final.

Uso:
    .venv/bin/python main.py

Ejecuta las 8 etapas del sistema en orden, mostrando cada resultado en
pantalla y guardando evidencias en la carpeta ``resultados/``:
tablas CSV, resumen JSON, gráficas PNG y esta misma bitácora.

Etapas:
  1. Descarga concurrente de las 4 APIs con asyncio.
  2. Limpieza y preparación con Pandas.
  3. Análisis de tráfico aéreo (12 análisis del documento).
  4. Análisis ambiental (sensores, clima y calidad del aire).
  5. Aceleración numérica (Numba/CuPy/NumPy) con benchmark real.
  6. Procesamiento distribuido con MPI.
  7. Visualización con Matplotlib.
  8. Respuestas a las 5 preguntas y conclusiones.
"""

import json
import subprocess
import sys
import time

sys.path.insert(0, str(__file__.rsplit("/", 1)[0]))

from config import N_PROCESOS_MPI, RESULTADOS_DIR
from datos import descarga
from procesamiento import aceleracion, analisis
from visualizacion import graficas


def titulo(n, texto):
    print("\n" + "=" * 70)
    print(f"PASO {n}: {texto}")
    print("=" * 70)


def main():
    t_global = time.perf_counter()
    resumen = {}

    # ---- Paso 1: descarga concurrente ------------------------------------
    titulo(1, "DESCARGA CONCURRENTE DE APIS (asyncio)")
    comp = descarga.comparar_descargas()
    datos = comp.pop("datos")
    resumen["tiempos_descarga"] = {k: round(v, 3) for k, v in comp.items()}
    vuelos_raw, f_vuelos = datos["vuelos"]
    sensores_raw, f_sens = datos["sensores"]
    clima_raw, f_clima = datos["clima"]
    aire_raw, f_aire = datos["aire"]
    print(f"Pipeline completo — secuencial: {comp['secuencial']:.2f} s | "
          f"concurrente: {comp['concurrente']:.2f} s")
    print(f"Canales ThingSpeak (red real) — secuencial: "
          f"{comp['canales_secuencial']:.2f} s | concurrente: "
          f"{comp['canales_concurrente']:.2f} s | "
          f"Speedup asyncio: {comp['canales_secuencial'] / max(comp['canales_concurrente'], 1e-6):.2f}x")
    print(f"Vuelos: {len(vuelos_raw)} registros [{f_vuelos}]")
    print(f"Sensores: {len(sensores_raw)} lecturas [{f_sens}]")
    print(f"Clima: {len(clima_raw)} ciudades [{f_clima}]")
    print(f"Calidad del aire: {len(aire_raw)} estaciones [{f_aire}]")
    resumen["fuentes"] = {"vuelos": f_vuelos, "sensores": f_sens,
                          "clima": f_clima, "aire": f_aire}

    # ---- Paso 2: limpieza -------------------------------------------------
    titulo(2, "LIMPIEZA Y PREPARACIÓN (Pandas)")
    vuelos = analisis.limpiar_vuelos(vuelos_raw)
    sensores = analisis.limpiar_sensores(sensores_raw)
    print(f"Vuelos limpios: {len(vuelos)} (antes: {len(vuelos_raw)})")
    print(f"Sensores limpios: {len(sensores)} lecturas, "
          f"columnas: {list(sensores.columns)}")
    vuelos.to_csv(RESULTADOS_DIR / "vuelos_limpios.csv", index=False)
    sensores.to_csv(RESULTADOS_DIR / "sensores_limpios.csv", index=False)
    clima_raw.to_csv(RESULTADOS_DIR / "clima_ciudades.csv", index=False)
    aire_raw.to_csv(RESULTADOS_DIR / "calidad_aire.csv", index=False)
    print("Tablas guardadas en resultados/*.csv")

    # ---- Paso 3: análisis de vuelos ---------------------------------------
    titulo(3, "ANÁLISIS DE TRÁFICO AÉREO (12 análisis)")
    res = {}
    res["activos_region"] = analisis.vuelos_activos_por_region(vuelos)
    print("a) Vuelos activos por región:\n", res["activos_region"].to_string())
    canc = analisis.vuelos_cancelados(vuelos)
    print(f"\nb) Cancelados: {canc['total']} ({canc['porcentaje']}%)")
    print("   Por aerolínea:\n", canc["por_aerolinea"].to_string())
    res["rutas_top"] = analisis.rutas_mas_frecuentes(vuelos)
    print("\nc) Rutas más frecuentes:\n", res["rutas_top"].to_string())
    res["por_aerolinea"] = analisis.vuelos_por_aerolinea(vuelos)
    print("\nd) Vuelos por aerolínea:\n", res["por_aerolinea"].to_string())
    sal_lleg = analisis.salidas_llegadas_por_aeropuerto(vuelos)
    print("\ne) Salidas y llegadas por aeropuerto:\n", sal_lleg.to_string())
    vel_alt = analisis.velocidad_altitud_promedio(vuelos)
    print(f"\nf) En vuelo ahora: {vel_alt['n_activos']} aviones | "
          f"velocidad prom: {vel_alt['velocidad_promedio_kmh']} km/h | "
          f"altitud prom: {vel_alt['altitud_promedio_ft']} ft")
    res["retrasos_aeropuerto"] = analisis.retrasos_por_aeropuerto(vuelos)
    print("\ng) Retrasos por aeropuerto:\n",
          res["retrasos_aeropuerto"].to_string())
    res["clima_retrasos"] = analisis.relacion_clima_retrasos(vuelos)
    print("\nh) Retraso promedio según clima:\n",
          res["clima_retrasos"]["por_clima"].to_string())
    print(f"   Correlación lluvia-retraso: "
          f"{res['clima_retrasos']['correlacion_lluvia_retraso']}")
    res["actividad_hora"] = analisis.actividad_por_hora(vuelos)
    print(f"\ni) Hora pico de actividad: {int(res['actividad_hora'].idxmax())}:00 "
          f"({int(res['actividad_hora'].max())} vuelos)")
    ficha = analisis.detalle_vuelo(vuelos, vuelos.iloc[0]["vuelo"])
    print(f"\nj) Ficha del vuelo {ficha['vuelo']}: {ficha}")
    sim = analisis.simular_ruta("MEX", "MAD")
    print(f"\nk) Simulación de ruta MEX→MAD: {sim['distancia_km']} km, "
          f"~{sim['tiempo_estimado_min']} min de vuelo.")
    atip = analisis.valores_atipicos(vuelos)
    print(f"\nl) Valores atípicos: "
          f"{ {k: v['n'] for k, v in atip.items()} } (detalle en JSON)")
    resumen["cancelados"] = {"total": canc["total"],
                             "porcentaje": canc["porcentaje"]}
    resumen["velocidad_altitud"] = vel_alt
    resumen["outliers"] = {k: {"n": v["n"], "z_max": v["z_max"]}
                           for k, v in atip.items()}
    resumen["simulacion_MEX_MAD"] = sim

    # ---- Paso 4: análisis ambiental ---------------------------------------
    titulo(4, "ANÁLISIS AMBIENTAL (sensores + clima + aire)")
    res_sens = analisis.resumen_sensores(sensores)
    print("Estadísticos de sensores:\n", res_sens.to_string())
    picos = analisis.picos_contaminacion(sensores)
    if picos is not None and len(picos):
        print(f"\nHora con mayor PM2.5: {int(picos.index[0])}:00 "
              f"({picos.iloc[0]:.1f} µg/m³)")
    print("\nClima por ciudad:\n", clima_raw.to_string(index=False))
    print("\nCalidad del aire por estación:\n", aire_raw.to_string(index=False))

    # ---- Paso 5: aceleración ----------------------------------------------
    titulo(5, "ACELERACIÓN NUMÉRICA (CuPy / Numba / NumPy)")
    print(f"Motor activo: {aceleracion.motor_aceleracion()}")
    bench = aceleracion.benchmark_aceleracion()
    print("Tiempos (z-score, 300 mil datos):", bench["tiempos"])
    print("Speedup vs Python puro:", bench["speedup_vs_python"])
    resumen["benchmark_aceleracion"] = bench

    # ---- Paso 6: MPI -------------------------------------------------------
    titulo(6, f"PROCESAMIENTO DISTRIBUIDO (MPI, {N_PROCESOS_MPI} procesos)")
    salida_mpi = _ejecutar_mpi()
    print(salida_mpi)
    resumen["mpi"] = salida_mpi.strip().splitlines()[-3:]

    # ---- Paso 7: visualización ----------------------------------------------
    titulo(7, "VISUALIZACIÓN (Matplotlib)")
    pngs = graficas.generar_todas(
        vuelos, sensores, res,
        {"secuencial": comp["canales_secuencial"],
         "concurrente": comp["canales_concurrente"]})
    for p in pngs:
        print(f"   gráfica: resultados/{p}")
    resumen["graficas"] = pngs

    # ---- Paso 8: preguntas y conclusiones ------------------------------------
    titulo(8, "RESPUESTAS A LAS 5 PREGUNTAS DEL PROYECTO")
    respuestas = analisis.responder_preguntas(vuelos, sensores, clima_raw)
    resumen["respuestas"] = respuestas
    for i, (preg, resp) in enumerate(respuestas.items(), 1):
        print(f"\n{i}. {preg}\n   → {resp}")

    with open(RESULTADOS_DIR / "resumen_resultados.json", "w") as f:
        json.dump(resumen, f, indent=2, ensure_ascii=False, default=str)
    print("\n" + "=" * 70)
    print(f"PIPELINE COMPLETO en {time.perf_counter() - t_global:.1f} s. "
          f"Evidencias en: {RESULTADOS_DIR}")
    print("=" * 70)


def _ejecutar_mpi():
    """Intenta mpiexec con N procesos; si falla, modo de un proceso."""
    try:
        r = subprocess.run(
            ["mpiexec", "-n", str(N_PROCESOS_MPI), sys.executable,
             "-m", "procesamiento.mpi_analisis"],
            capture_output=True, text=True, timeout=120,
            cwd=str(__file__.rsplit("/", 1)[0]))
        if r.returncode == 0 and "CORRECTO" in r.stdout:
            return r.stdout
        print(f"   [MPI] mpiexec no disponible aquí ({r.returncode}); "
              f"usando 1 proceso.")
    except Exception as exc:
        print(f"   [MPI] mpiexec no disponible aquí ({exc}); usando 1 proceso.")
    r = subprocess.run([sys.executable, "-m", "procesamiento.mpi_analisis"],
                       capture_output=True, text=True, timeout=120,
                       cwd=str(__file__.rsplit("/", 1)[0]))
    return r.stdout + r.stderr


if __name__ == "__main__":
    main()

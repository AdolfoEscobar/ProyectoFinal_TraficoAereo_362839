"""Pruebas del proyecto (no necesitan red ni claves).

Uso:
    .venv/bin/python -m pytest pruebas/ -v
    # o sin pytest:
    .venv/bin/python pruebas/test_analisis.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datos import generador
from procesamiento import aceleracion, analisis


def test_generador_vuelos():
    df = generador.generar_vuelos(500)
    assert len(df) == 500
    assert (df["origen"] != df["destino"]).all(), "origen == destino"
    assert df["retraso_min"].min() >= 0
    # Los cancelados no acumulan retraso.
    assert (df.loc[df["estado"] == "cancelado", "retraso_min"] == 0).all()
    print("ok: generador de vuelos")


def test_generador_sensores():
    df = generador.generar_sensores(48)
    assert len(df) == 48
    assert df["pm25"].min() >= 0 and df["pm10"].min() >= 0
    assert df["humedad"].between(0, 100).all()
    print("ok: generador de sensores")


def test_limpieza_y_analisis():
    df = analisis.limpiar_vuelos(generador.generar_vuelos(300))
    assert len(df) > 0
    assert len(analisis.vuelos_activos_por_region(df)) > 0
    assert len(analisis.rutas_mas_frecuentes(df)) > 0
    assert len(analisis.vuelos_por_aerolinea(df)) > 0
    va = analisis.velocidad_altitud_promedio(df)
    assert va["n_activos"] > 0 and va["velocidad_promedio_kmh"] > 0
    rel = analisis.relacion_clima_retrasos(df)
    assert -1 <= rel["correlacion_lluvia_retraso"] <= 1
    print("ok: limpieza y análisis básicos")


def test_detalle_y_simulacion():
    df = analisis.limpiar_vuelos(generador.generar_vuelos(300))
    ficha = analisis.detalle_vuelo(df, df.iloc[0]["vuelo"])
    assert ficha is not None and "ruta" in ficha
    assert analisis.detalle_vuelo(df, "NO-EXISTE") is None
    sim = analisis.simular_ruta("MEX", "MAD")
    assert 8000 < sim["distancia_km"] < 10000, sim  # ~9,000 km reales
    assert analisis.simular_ruta("XXX", "YYY") is None
    print("ok: detalle de vuelo y simulación de ruta")


def test_outliers_acelerados():
    df = analisis.limpiar_vuelos(generador.generar_vuelos(1500))
    atip = analisis.valores_atipicos(df)
    # El generador planta 3 atípicos intencionales; deben detectarse.
    assert atip["velocidad_kmh"]["n"] >= 1
    assert atip["altitud_ft"]["n"] >= 1
    assert atip["retraso_min"]["n"] >= 1
    print(f"ok: outliers { {k: v['n'] for k, v in atip.items()} } "
          f"[{aceleracion.motor_aceleracion()}]")


def test_preguntas():
    vuelos = analisis.limpiar_vuelos(generador.generar_vuelos(300))
    sensores = analisis.limpiar_sensores(generador.generar_sensores(48))
    resp = analisis.responder_preguntas(vuelos, sensores, None)
    assert len(resp) == 5 and all(len(v) > 20 for v in resp.values())
    print("ok: 5 preguntas respondidas")


def test_mpi_parciales():
    # Lógica de combinación MPI sin necesidad de mpiexec.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mpi_analisis", Path(__file__).resolve().parent.parent
        / "procesamiento" / "mpi_analisis.py")
    mpi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mpi)
    df = analisis.limpiar_vuelos(generador.generar_vuelos(100))
    filas = df.to_dict("records")
    mitad = len(filas) // 2
    total = mpi.combinar([mpi.parcial_por_trozo(filas[:mitad]),
                          mpi.parcial_por_trozo(filas[mitad:])])
    assert sum(total["por_region"].values()) == len(filas)
    assert total["activos"] == int((df["estado"] == "activo").sum())
    print("ok: lógica scatter/gather de MPI")


if __name__ == "__main__":
    test_generador_vuelos()
    test_generador_sensores()
    test_limpieza_y_analisis()
    test_detalle_y_simulacion()
    test_outliers_acelerados()
    test_preguntas()
    test_mpi_parciales()
    print("\nTodas las pruebas pasaron ✔")

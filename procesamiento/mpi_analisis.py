"""Procesamiento distribuido con MPI4Py (scatter / gather).

Uso:
    mpiexec -n 4 .venv/bin/python -m procesamiento.mpi_analisis

También funciona sin mpiexec (un solo proceso) para comprobar la lógica.

Qué hace: el proceso 0 (raíz) carga la tabla de vuelos y la reparte en
trozos entre todos los procesos con ``scatter``. Cada proceso calcula
estadísticos parciales de su trozo (vuelos por región, retraso acumulado
por aeropuerto, activos y cancelados) y los devuelve con ``gather``.
El proceso 0 combina los parciales, los compara con el cálculo secuencial
de Pandas y reporta si coinciden (verificación de corrección).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mpi4py import MPI

from datos import generador
from procesamiento import analisis


def parcial_por_trozo(trozo):
    """Estadísticos parciales que calcula cada proceso MPI."""
    por_region, retr_suma, retr_n = {}, {}, {}
    activos = cancelados = 0
    for v in trozo:
        por_region[v["region"]] = por_region.get(v["region"], 0) + 1
        if v["estado"] == "activo":
            activos += 1
        if v["estado"] == "cancelado":
            cancelados += 1
        else:
            o = v["origen"]
            retr_suma[o] = retr_suma.get(o, 0.0) + float(v["retraso_min"])
            retr_n[o] = retr_n.get(o, 0) + 1
    return {"por_region": por_region, "retr_suma": retr_suma,
            "retr_n": retr_n, "activos": activos, "cancelados": cancelados}


def combinar(parciales):
    """Une los diccionarios parciales de todos los procesos."""
    total = {"por_region": {}, "retr_suma": {}, "retr_n": {},
             "activos": 0, "cancelados": 0}
    for p in parciales:
        for k, v in p["por_region"].items():
            total["por_region"][k] = total["por_region"].get(k, 0) + v
        for k, v in p["retr_suma"].items():
            total["retr_suma"][k] = total["retr_suma"].get(k, 0.0) + v
        for k, v in p["retr_n"].items():
            total["retr_n"][k] = total["retr_n"].get(k, 0) + v
        total["activos"] += p["activos"]
        total["cancelados"] += p["cancelados"]
    return total


def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    t0 = time.perf_counter()

    # El proceso 0 prepara y reparte; los demás reciben su trozo.
    if rank == 0:
        df = analisis.limpiar_vuelos(generador.generar_vuelos())
        filas = df.to_dict("records")
        trozos = [filas[i::size] for i in range(size)]  # Reparto parejo.
        n_total = len(filas)
    else:
        trozos = None
        n_total = 0
    n_total = comm.bcast(n_total, root=0)
    mi_trozo = comm.scatter(trozos, root=0)

    # Cada proceso trabaja su parte sin comunicarse con nadie.
    mi_parcial = parcial_por_trozo(mi_trozo)
    print(f"   [MPI] proceso {rank}/{size}: procesó {len(mi_trozo)} vuelos.",
          flush=True)

    # Recolección y combinación en el proceso 0.
    parciales = comm.gather(mi_parcial, root=0)
    duracion = time.perf_counter() - t0

    if rank == 0:
        total = combinar(parciales)
        retraso_prom = {a: round(total["retr_suma"][a] / total["retr_n"][a], 2)
                        for a in total["retr_suma"]}
        print(f"\n[MPI] {size} procesos terminaron en {duracion:.3f} s "
              f"({n_total} vuelos).")
        print(f"[MPI] Activos: {total['activos']} | "
              f"Cancelados: {total['cancelados']}")
        print(f"[MPI] Por región: {total['por_region']}")
        print(f"[MPI] Retraso promedio por aeropuerto: {retraso_prom}")

        # Verificación: el resultado distribuido debe igualar al secuencial.
        ref_region = analisis.vuelos_activos_por_region(df).to_dict()
        # Nota: MPI cuenta todos los vuelos por región; se compara el total.
        ref_total = df.groupby("region").size().to_dict()
        ok = (total["por_region"] == ref_total
              and total["activos"] == int((df["estado"] == "activo").sum())
              and total["cancelados"] == int((df["estado"] == "cancelado").sum()))
        print(f"[MPI] Verificación contra cálculo secuencial: "
              f"{'CORRECTO ✔' if ok else 'DIFERENTE ✘'} "
              f"(activos ref={ref_region})")


if __name__ == "__main__":
    main()

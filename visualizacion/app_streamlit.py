"""Tablero interactivo con Streamlit (visualización opcional).

Uso:
    .venv/bin/python -m streamlit run visualizacion/app_streamlit.py

Muestra los resultados ya calculados por ``main.py`` (lee los CSV de la
carpeta ``resultados/``), así que primero hay que ejecutar el pipeline.
Streamlit es opcional: si no está instalado, el proyecto funciona igual
con las gráficas de Matplotlib.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from config import RESULTADOS_DIR

try:
    import streamlit as st
except ImportError:
    raise SystemExit("Instala streamlit para usar el tablero: "
                     "pip install streamlit")


st.set_page_config(page_title="Tráfico aéreo y ambiente — 362839",
                   layout="wide")
st.title("✈️ Tráfico aéreo y condiciones ambientales")
st.caption("Adolfo Escobar Pereyra · Matrícula 362839 · "
           "Cómputo Paralelo y Distribuido")

vuelos = pd.read_csv(RESULTADOS_DIR / "vuelos_limpios.csv")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Vuelos", len(vuelos))
col2.metric("Activos", int((vuelos["estado"] == "activo").sum()))
col3.metric("Cancelados", int((vuelos["estado"] == "cancelado").sum()))
col4.metric("Retraso promedio (min)",
            round(vuelos["retraso_min"].mean(), 1))

tab1, tab2, tab3 = st.tabs(["Regiones y aerolíneas", "Retrasos y clima",
                            "Detalle de vuelo"])
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Activos por región")
        st.bar_chart(vuelos[vuelos["estado"] == "activo"]
                     .groupby("region").size())
    with c2:
        st.subheader("Vuelos por aerolínea")
        st.bar_chart(vuelos.groupby("aerolinea").size())
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Retraso promedio por aeropuerto")
        st.bar_chart(vuelos.groupby("origen")["retraso_min"].mean())
    with c2:
        st.subheader("Retraso promedio según clima")
        st.bar_chart(vuelos.groupby("clima")["retraso_min"].mean())
    st.subheader("Actividad por hora")
    st.line_chart(vuelos.groupby("hora").size())
with tab3:
    vuelo_id = st.selectbox("Elige un vuelo", sorted(vuelos["vuelo"].unique()))
    st.dataframe(vuelos[vuelos["vuelo"] == vuelo_id].T.rename(columns={0: "valor"}))

st.divider()
st.caption("Fuente: AirLabs/ThingSpeak/OpenWeather/OpenAQ o datos simulados "
           "cuando no hay clave. Procesado con asyncio, MPI4Py, Numba y Pandas.")

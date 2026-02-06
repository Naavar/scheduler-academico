import os
import io
import json
import tempfile

import streamlit as st
import pandas as pd

from extractor_pdf import procesar_todo_automaticamente
from buscador_huecos import BuscadorHuecos

st.set_page_config(page_title="Buscador de huecos")
st.title("Sistema de Búsqueda de Huecos en Horarios")

if "datos_horarios" not in st.session_state:
    st.session_state["datos_horarios"] = None
if "ultimo_resultado" not in st.session_state:
    st.session_state["ultimo_resultado"] = []

st.header("1. Cargar horarios en PDF")

archivos_pdf = st.file_uploader(
    "Selecciona uno o varios PDFs de horarios de profesores",
    type=["pdf"],
    accept_multiple_files=True,
)

if st.button("Cargar horarios desde PDF"):
    if not archivos_pdf:
        st.error("Primero selecciona al menos un archivo PDF.")
    else:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                for archivo_pdf in archivos_pdf:
                    ruta_pdf = os.path.join(tmpdir, archivo_pdf.name)
                    with open(ruta_pdf, "wb") as f:
                        f.write(archivo_pdf.getbuffer())

                horarios = procesar_todo_automaticamente(tmpdir)

            profesores = []
            for entrada in horarios:
                if "profesor" not in entrada or "eventos" not in entrada:
                    continue
                profesores.append(
                    {
                        "profesor": entrada["profesor"],
                        "eventos": entrada["eventos"],
                    }
                )

            if not profesores:
                st.error("No se ha podido extraer ningún horario válido de los PDFs seleccionados.")
            else:
                st.session_state["datos_horarios"] = {"profesores": profesores}
                nombres = [p["profesor"].get("nombre", "SIN_NOMBRE") for p in profesores]
                st.success(f"Se han cargado {len(profesores)} profesores desde PDF.")
                st.write(nombres)
        except Exception as e:
            st.error(f"Error al procesar los PDFs: {e}")

datos = st.session_state.get("datos_horarios")

st.header("2. Parámetros de búsqueda")

duracion = st.slider("Duración de la reunión (minutos):", 30, 120, 60, 15)

dia_opciones = ["Todos", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
dia_seleccionado = st.selectbox("Día:", dia_opciones)

turno = st.radio("Turno:", ["Todos", "Mañana", "Tarde"])

st.header("3. Búsqueda de huecos y resultados")

col_buscar, col_exportar = st.columns([2, 1])

with col_buscar:
    if st.button("Buscar huecos comunes"):
        if not datos or not datos.get("profesores"):
            st.error("Primero debes cargar los horarios desde PDF.")
        else:
            buscador = BuscadorHuecos(datos["profesores"])
            filtro_dia = None if dia_seleccionado == "Todos" else dia_seleccionado
            filtro_dia = None if dia_seleccionado == "Todos" else dia_seleccionado

            if turno == "Todos":
                filtro_turno = None
            elif turno == "Mañana":
                filtro_turno = "mañana"
            else:
                filtro_turno = "tarde"

            huecos = buscador.buscar_huecos_por_profesor(
                duracion=duracion,
                filtro_dia=filtro_dia,
                turno=filtro_turno,
                hora_min=None,
                hora_max=None,
            )

            st.session_state["ultimo_resultado"] = huecos
            if not huecos:
                st.warning("No se han encontrado huecos comunes con los parámetros seleccionados.")
            else:
                st.success(f"Se han encontrado {len(huecos)} huecos.")

                filas_top = []
                for h in huecos:
                    filas_top.append(
                        {
                            "Día": h.dia,
                            "Hora Inicio": h.hora_inicio,
                            "Hora Fin": h.hora_fin,
                            "Profesores": ", ".join(h.profesores_disponibles),
                            "Total": h.num_profesores,
                        }
                    )

                df_top = pd.DataFrame(filas_top)
                st.subheader("Top 5 mejores huecos")
                st.dataframe(df_top)

                with st.expander("Ver lista completa de profesores por hueco"):
                    for h in huecos:
                        st.markdown(
                            f"**{h.dia} {h.hora_inicio}-{h.hora_fin}** "
                            f"({h.num_profesores} profesores)"
                        )
                        st.write(", ".join(h.profesores_disponibles))

with col_exportar:
    if st.button("Exportar a Excel"):
        huecos = st.session_state.get("ultimo_resultado", [])
        if not huecos:
            st.error("No hay resultados que exportar. Busca huecos primero.")
        else:
            filas_excel = []
            for h in huecos:
                filas_excel.append(
                    {
                        "Día": h.dia,
                        "Hora Inicio": h.hora_inicio,
                        "Hora Fin": h.hora_fin,
                        "Profesores": ", ".join(h.profesores_disponibles),
                        "Total": h.num_profesores,
                    }
                )
            df_excel = pd.DataFrame(filas_excel)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_excel.to_excel(writer, index=False, sheet_name="Huecos")
            buffer.seek(0)
            st.download_button(
                label="Descargar Excel",
                data=buffer,
                file_name="huecos_comunes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

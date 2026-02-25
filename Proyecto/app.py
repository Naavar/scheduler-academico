import os
import io
import tempfile

import streamlit as st
import pandas as pd

from extractor_pdf import procesar_todo_automaticamente
from buscador_evaluacion import buscar_sesion_evaluacion

st.set_page_config(page_title="Sesión de Evaluación", layout="wide")
st.title("Buscador de Sesión de Evaluación")

# ---------------------------------------------------------------------------
# ESTADO
# ---------------------------------------------------------------------------

if "profesores" not in st.session_state:
    st.session_state["profesores"] = []

if "resultado" not in st.session_state:
    st.session_state["resultado"] = None

# ---------------------------------------------------------------------------
# PASO 1: CARGAR PDF
# ---------------------------------------------------------------------------

st.header("1. Cargar horarios")

archivos_pdf = st.file_uploader(
    "Selecciona uno o varios PDFs de horarios",
    type=["pdf"],
    accept_multiple_files=True,
)

if st.button("Cargar horarios desde PDF"):
    if not archivos_pdf:
        st.error("Selecciona al menos un PDF.")
    else:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                for archivo in archivos_pdf:
                    ruta = os.path.join(tmpdir, archivo.name)
                    with open(ruta, "wb") as f:
                        f.write(archivo.getbuffer())
                horarios = procesar_todo_automaticamente(tmpdir)

            profesores = [
                {"profesor": e["profesor"], "eventos": e["eventos"]}
                for e in horarios
                if "profesor" in e and "eventos" in e
            ]

            if not profesores:
                st.error("No se pudo extraer ningún horario válido.")
            else:
                st.session_state["profesores"] = profesores
                st.session_state["resultado"] = None
                st.success(f"{len(profesores)} profesores cargados correctamente.")

        except Exception as e:
            st.error(f"Error al procesar los PDFs: {e}")

# ---------------------------------------------------------------------------
# PASO 2: SELECCIONAR EQUIPO
# ---------------------------------------------------------------------------

profesores = st.session_state["profesores"]

if profesores:
    st.header("2. Seleccionar equipo educativo")

    nombres_disponibles = [
        p["profesor"].get("nombre", p["profesor"].get("codigo", "SIN_NOMBRE"))
        for p in profesores
    ]
    codigos_por_nombre = {
        p["profesor"].get("nombre", p["profesor"].get("codigo", "SIN_NOMBRE")): p["profesor"]["codigo"]
        for p in profesores
    }

    seleccionados = st.multiselect(
        "Selecciona los profesores del equipo:",
        options=nombres_disponibles,
    )

    # ---------------------------------------------------------------------------
    # PASO 3: BUSCAR
    # ---------------------------------------------------------------------------

    st.header("3. Buscar sesión de evaluación")

    RECREOS = {"11:00", "14:15", "18:05"}

    if st.button("Buscar sesión óptima"):
        if not seleccionados:
            st.error("Selecciona al menos un profesor.")
        else:
            equipo_codigos = {codigos_por_nombre[nombre] for nombre in seleccionados}

            resultado = buscar_sesion_evaluacion(
                profesores=profesores,
                equipo_codigos=equipo_codigos,
                recreos=RECREOS,
            )

            st.session_state["resultado"] = resultado

    # ---------------------------------------------------------------------------
    # PASO 4: MOSTRAR RESULTADO
    # ---------------------------------------------------------------------------

    resultado = st.session_state["resultado"]

    if resultado is not None:
        st.header("4. Resultado")

        if resultado.sin_solucion:
            st.error(f"Sin solución: {resultado.explicacion}")
        else:
            st.success(
                f"✅ Slot óptimo: **{resultado.dia}** de **{resultado.hora_inicio}** a **{resultado.hora_fin}**"
            )

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Coste total", resultado.coste_total)
            with col2:
                st.metric("Peor penalización", resultado.peor_penalizacion)

            st.subheader("Detalle por profesor")

            filas = []
            for d in resultado.detalle:
                cercana = (
                    f"{d.sesion_ocupada_mas_cercana[0]} - {d.sesion_ocupada_mas_cercana[1]}"
                    if d.sesion_ocupada_mas_cercana
                    else "—"
                )
                filas.append({
                    "Profesor": d.nombre,
                    "Penalización": d.penalizacion,
                    "Sesión más cercana": cercana,
                    "Tiene eventos ese día": "Sí" if d.tiene_eventos_ese_dia else "No",
                })

            df = pd.DataFrame(filas)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Exportar
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Evaluación")
            buffer.seek(0)

            st.download_button(
                label="Exportar a Excel",
                data=buffer,
                file_name="sesion_evaluacion.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
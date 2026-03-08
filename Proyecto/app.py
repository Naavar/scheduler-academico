import os
import io
import tempfile

import streamlit as st
import pandas as pd

from extractor_pdf import procesar_todo_automaticamente
from config import Config, todos_dias

TODOS_DIAS = todos_dias
from buscador_evaluacion import buscar_sesion_evaluacion

st.set_page_config(page_title="Sesión de Evaluación", layout="wide")
st.title("Buscador de Sesión de Evaluación")

def build_config_from_params(
    nivel, dias, hora_recreo, sesiones_por_dia,
    permitir_septima_hora, permitir_recreo, permitir_horas_no_obligatorias
) -> Config:
    return Config(
        hora_recreo=hora_recreo,
        sesiones_por_dia=sesiones_por_dia,
        permitir_septima_hora=permitir_septima_hora,
        permitir_recreo=permitir_recreo,
        permitir_horas_no_obligatorias=permitir_horas_no_obligatorias,
        dias_disponibles_por_nivel={nivel: dias},
    )

def resolver_recreos(profesores: list, hora_recreo_sesion: int, permitir_recreo: bool) -> set:
    """
    Extrae las horas de inicio reales de la sesión número `hora_recreo_sesion`
    a partir de los eventos cargados de los PDFs, y las devuelve como set de strings.
    Si permitir_recreo=True devuelve set vacío (no se excluye nada).
    """
    if permitir_recreo:
        return set()

    # Recopilar todos los puntos de inicio ordenados (sin duplicados)
    puntos: set = set()
    for prof in profesores:
        for evento in prof.get("eventos", []):
            ini = evento.get("inicio", "").strip()
            if ini:
                puntos.add(ini)

    puntos_ordenados = sorted(puntos, key=lambda h: int(h.split(":")[0]) * 60 + int(h.split(":")[1]))

    # La sesión N corresponde al (N-1)-ésimo punto de inicio
    idx = hora_recreo_sesion - 1
    if 0 <= idx < len(puntos_ordenados):
        return {puntos_ordenados[idx]}

    return set()




with st.sidebar:
    st.header("⚙️ Configuración")

    with st.expander("🏫 Nivel y días", expanded=True):
        nivel = st.selectbox(
            "Nivel del grupo",
            options=["ESO", "BACH", "FP", "1FP", "2FP"],
        )
        # TODO Sprint 1: sustituir TODOS_DIAS por config.get_dias_nivel(nivel)
        # cuando Lucas tenga inferir_nivel() funcionando
        dias = st.multiselect(
            "Días disponibles para evaluación",
            options=TODOS_DIAS,
            default=TODOS_DIAS,
        )

    with st.expander("🕐 Jornada lectiva", expanded=True):
        sesiones_por_dia = st.selectbox(
            "Sesiones por día",
            options=[5, 6, 7, 8],
            index=2,
        )
        hora_recreo = st.selectbox(
            "Sesión del recreo",
            options=list(range(1, sesiones_por_dia + 1)),
            index=3,
        )
        duracion_minutos = st.slider(
            "Duración de la reunión (minutos)",
            min_value=30,
            max_value=120,
            value=55,
            step=5,
            help="El buscador encontrará un bloque contiguo libre de al menos esta duración.",
        )

    with st.expander("🚦 Restricciones", expanded=True):
        permitir_septima_hora = st.checkbox(
            "¿Permitir 7ª hora?",
            value=False,
            help="ℹ️ Actívalo solo si el centro admite reuniones en la última sesión.",
        )
        permitir_recreo = st.checkbox("¿Permitir recreo?", value=False)
        if permitir_recreo:
            st.warning("⚠️ El recreo es tiempo de descanso del profesorado.")
        permitir_horas_no_obligatorias = st.checkbox(
            "¿Incluir horas fuera de permanencia?", value=False
        )

    config = build_config_from_params(
        nivel=nivel,
        dias=dias,
        hora_recreo=hora_recreo,
        sesiones_por_dia=sesiones_por_dia,
        permitir_septima_hora=permitir_septima_hora,
        permitir_recreo=permitir_recreo,
        permitir_horas_no_obligatorias=permitir_horas_no_obligatorias,
    )

st.title("Sistema de Búsqueda de Huecos en Horarios")
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

    if st.button("Buscar sesión óptima"):
        if not seleccionados:
            st.error("Selecciona al menos un profesor.")
        else:
            equipo_codigos = {codigos_por_nombre[nombre] for nombre in seleccionados}

            # Recreo: calculado dinámicamente desde los horarios cargados
            recreos = resolver_recreos(profesores, config.hora_recreo, config.permitir_recreo)

            # Días con 7ª hora: si no se permite, excluir la última sesión
            # filtrando los candidatos por sesiones_por_dia (se gestiona en buscador vía config)
            resultado = buscar_sesion_evaluacion(
                profesores=profesores,
                equipo_codigos=equipo_codigos,
                recreos=recreos,
                dias_disponibles=dias if dias else None,
                duracion_minutos=duracion_minutos,
            )

            st.session_state["resultado"] = resultado

    # ---------------------------------------------------------------------------
    # PASO 4: MOSTRAR RESULTADO
    # ---------------------------------------------------------------------------

    resultado = st.session_state["resultado"]

    if resultado is not None:
        st.header("4. Resultado")

        if resultado.sin_solucion:
            st.error(f"❌ Sin solución: {resultado.explicacion}")

            if resultado.diagnostico_bloqueadores:
                st.subheader("🔒 Profesores que bloquean más slots")
                st.caption("Indica cuántos franjas horarias bloquea cada profesor. Los primeros son los que más dificultan encontrar un hueco común.")

                filas_diag = [
                    {"Profesor": nombre, "Slots bloqueados": num_slots}
                    for nombre, num_slots in resultado.diagnostico_bloqueadores
                ]
                df_diag = pd.DataFrame(filas_diag)
                st.dataframe(df_diag, use_container_width=True, hide_index=True)
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
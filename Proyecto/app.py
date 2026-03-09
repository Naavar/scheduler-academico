import os
import io
import json
import tempfile

import streamlit as st
import pandas as pd

from extractor_pdf import procesar_todo_automaticamente
from config import Config, todos_dias

TODOS_DIAS = todos_dias
from buscador_evaluacion import buscar_sesion_evaluacion

# ---------------------------------------------------------------------------
# NIVELES DESDE JSON
# ---------------------------------------------------------------------------

def _encontrar_json() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(base, "..", "data", "horarios_consolidados.json"),
        os.path.join(os.getcwd(), "..", "data", "horarios_consolidados.json"),
        os.path.join(os.getcwd(), "data", "horarios_consolidados.json"),
    ]
    for ruta in candidatos:
        if os.path.isfile(ruta):
            return os.path.normpath(ruta)
    return os.path.normpath(candidatos[0])


@st.cache_data
def cargar_datos_desde_json(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            datos = json.load(f)
        grupos_por_nivel = {}
        grupos_por_codigo = {}
        for entrada in datos:
            codigo = entrada.get("profesor", {}).get("codigo", "")
            grupos = entrada.get("grupos", {})
            if codigo:
                grupos_por_codigo[codigo] = grupos
            for nivel, cursos in grupos.items():
                grupos_por_nivel.setdefault(nivel, set()).update(cursos)
        niveles = sorted(grupos_por_nivel.keys())
        grupos_por_nivel = {n: sorted(g) for n, g in grupos_por_nivel.items()}
        return (niveles or ["ESO", "BACH", "FP"]), grupos_por_nivel, grupos_por_codigo
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.warning(f"⚠️ No se pudo cargar `{path}` ({e}). Usando niveles por defecto.")
        return ["ESO", "BACH", "FP"], {}, {}


NIVELES_DISPONIBLES, GRUPOS_POR_NIVEL, GRUPOS_POR_CODIGO = cargar_datos_desde_json(_encontrar_json())

st.set_page_config(page_title="Sesión de Evaluación", layout="wide")
st.title("Buscador de Sesión de Evaluación")


def build_config_from_params(
    nivel, dias, hora_recreo,
    permitir_septima_hora, permitir_recreo, permitir_horas_no_obligatorias
) -> Config:
    return Config(
        hora_recreo=hora_recreo,
        sesiones_por_dia=7,
        permitir_septima_hora=permitir_septima_hora,
        permitir_recreo=permitir_recreo,
        permitir_horas_no_obligatorias=permitir_horas_no_obligatorias,
        dias_disponibles_por_nivel={nivel: dias},
    )


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Configuración")

    with st.expander("🏫 Nivel y días", expanded=True):
        nivel = st.selectbox("Nivel del grupo", options=NIVELES_DISPONIBLES)
        grupos_del_nivel = GRUPOS_POR_NIVEL.get(nivel, [])

        col_cb, col_btn = st.columns([3, 1])
        with col_cb:
            seleccionar_todos_cursos = st.checkbox(
                "Seleccionar todos los cursos", value=True, key="cb_todos_cursos",
                help="Marca todos por defecto.",
            )
        with col_btn:
            if st.button("Limpiar", key="btn_limpiar_cursos"):
                st.session_state["cursos_sel"] = []
                st.rerun()

        if seleccionar_todos_cursos:
            st.session_state["cursos_sel"] = grupos_del_nivel

        if "cursos_sel" not in st.session_state:
            st.session_state["cursos_sel"] = []

        cursos = st.multiselect(
            "Cursos",
            options=grupos_del_nivel,
            default=st.session_state["cursos_sel"],
        )
        st.session_state["cursos_sel"] = cursos

        dias = st.multiselect(
            "Días disponibles para evaluación",
            options=TODOS_DIAS,
            default=TODOS_DIAS,
        )

    duracion_minutos = st.slider(
        "⏱️ Duración de la reunión (minutos)",
        min_value=30, max_value=120, value=55, step=5,
    )

    sesiones_recreo = [4]

    with st.expander("🚦 Restricciones", expanded=True):
        permitir_septima_hora = st.checkbox("¿Permitir 7ª hora?", value=False)
        permitir_recreo = st.checkbox("¿Permitir recreo?", value=False)
        if permitir_recreo:
            st.warning("⚠️ El recreo es tiempo de descanso del profesorado.")
        permitir_horas_no_obligatorias = st.checkbox(
            "¿Incluir horas fuera de permanencia?", value=False
        )

    config = build_config_from_params(
        nivel=nivel,
        dias=dias,
        hora_recreo=sesiones_recreo[0] if sesiones_recreo else 4,
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

if "resultados_por_curso" not in st.session_state:
    st.session_state["resultados_por_curso"] = {}

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
# PASO 2: SELECCIONAR EQUIPO POR CURSO
# ---------------------------------------------------------------------------

profesores = st.session_state["profesores"]


def profesores_de_curso(curso_sel, nivel_sel):
    nombres, codigos = [], {}
    for p in profesores:
        codigo = p["profesor"]["codigo"]
        cursos_prof = set(GRUPOS_POR_CODIGO.get(codigo, {}).get(nivel_sel, []))
        if curso_sel in cursos_prof:
            nombre = p["profesor"].get("nombre", codigo)
            nombres.append(nombre)
            codigos[nombre] = codigo
    return nombres, codigos


if profesores:
    st.header("2. Equipo educativo por curso")
    st.caption(
        "Profesores preseleccionados automáticamente por curso. "
        "Puedes añadir o quitar individualmente."
    )

    equipos_por_curso = {}
    for curso in cursos:
        nombres_curso, _ = profesores_de_curso(curso, nivel)
        key_curso = f"equipo_{curso}"

        if key_curso not in st.session_state:
            st.session_state[key_curso] = nombres_curso

        nombres_disponibles_todos = [
            p["profesor"].get("nombre", p["profesor"].get("codigo", "SIN_NOMBRE"))
            for p in profesores
        ]

        with st.expander(
            f"📋 {curso} — {len(st.session_state[key_curso])} profesores",
            expanded=False,
        ):
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                seleccionados_curso = st.multiselect(
                    "Profesores:",
                    options=nombres_disponibles_todos,
                    default=st.session_state[key_curso],
                    key=f"ms_{curso}",
                )
            with col_btn:
                if st.button("Resetear", key=f"reset_{curso}"):
                    st.session_state[key_curso] = nombres_curso
                    st.rerun()
            st.session_state[key_curso] = seleccionados_curso
            equipos_por_curso[curso] = seleccionados_curso

    # ---------------------------------------------------------------------------
    # PASO 3: BUSCAR
    # ---------------------------------------------------------------------------

    st.header("3. Buscar sesión de evaluación")

    st.info(
        "ℹ️ Los cursos se procesan en orden. Si un profesor comparte cursos "
        "(ej. da clase a 2BACH-A y 2BACH-B), el slot asignado al primer curso "
        "se bloquea automáticamente antes de buscar el del siguiente, "
        "evitando que el profesor coincida en dos reuniones a la vez."
    )

    if st.button("Buscar sesión óptima para cada curso"):
        if not cursos:
            st.error("Selecciona al menos un curso en el sidebar.")
        else:
            codigos_por_nombre = {
                p["profesor"].get("nombre", p["profesor"].get("codigo", "SIN_NOMBRE")): p["profesor"]["codigo"]
                for p in profesores
            }

            resultados_por_curso = {}

            for curso in cursos:
                nombres_sel = st.session_state.get(f"equipo_{curso}", [])
                if not nombres_sel:
                    continue

                equipo_codigos = {
                    codigos_por_nombre[n]
                    for n in nombres_sel
                    if n in codigos_por_nombre
                }

                # ── CLAVE: pasar los resultados ya asignados ──────────────
                # El dict crece curso a curso. Cuando se busca 2BACH-B,
                # ya contiene el resultado de 2BACH-A y bloquea sus slots para evitar solapamiento.
                resultado = buscar_sesion_evaluacion(
                    profesores=profesores,
                    equipo_codigos=equipo_codigos,
                    config=config,
                    dias_disponibles=dias if dias else None,
                    duracion_minutos=duracion_minutos,
                    resultados_previos=resultados_por_curso,  # ← anti-solapamiento automático
                )
                resultados_por_curso[curso] = resultado

            st.session_state["resultados_por_curso"] = resultados_por_curso

    # ---------------------------------------------------------------------------
    # PASO 4: MOSTRAR RESULTADOS
    # ---------------------------------------------------------------------------

    resultados_por_curso = st.session_state.get("resultados_por_curso", {})

    if resultados_por_curso:
        st.header("4. Resultados por curso")

        filas_excel = []

        for curso, resultado in resultados_por_curso.items():
            if resultado.sin_solucion:
                with st.expander(f"❌ {curso} — Sin solución", expanded=False):
                    st.error(resultado.explicacion)
                    if resultado.diagnostico_bloqueadores:
                        st.subheader("🔒 Profesores que bloquean más slots")
                        df_diag = pd.DataFrame([
                            {"Profesor": n, "Slots bloqueados": s}
                            for n, s in resultado.diagnostico_bloqueadores
                        ])
                        st.dataframe(df_diag, use_container_width=True, hide_index=True)
            else:
                avisos = []
                if resultado.es_septima: avisos.append("⚠️ 7ª hora")
                if resultado.es_recreo:  avisos.append("⚠️ Recreo")
                aviso_str = "  " + " · ".join(avisos) if avisos else ""

                label = (
                    f"✅ {curso} — {resultado.dia} · "
                    f"{resultado.hora_inicio} a {resultado.hora_fin}{aviso_str}"
                )
                with st.expander(label, expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Coste total", resultado.coste_total)
                    with col2:
                        st.metric("Peor penalización", resultado.peor_penalizacion)

                    filas = []
                    for d in resultado.detalle:
                        cercana = (
                            f"{d.sesion_ocupada_mas_cercana[0]} - {d.sesion_ocupada_mas_cercana[1]}"
                            if d.sesion_ocupada_mas_cercana else "—"
                        )
                        filas.append({
                            "Profesor": d.nombre,
                            "Penalización": d.penalizacion,
                            "Sesión más cercana": cercana
                        })
                    df = pd.DataFrame(filas)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    for fila in filas:
                        filas_excel.append({
                            "Curso": curso,
                            "Día": resultado.dia,
                            "Hora inicio": resultado.hora_inicio,
                            "Hora fin": resultado.hora_fin,
                            **fila,
                        })

        if filas_excel:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                pd.DataFrame(filas_excel).to_excel(
                    writer, index=False, sheet_name="Evaluación"
                )
            buffer.seek(0)
            st.download_button(
                label="📥 Exportar todos los resultados a Excel",
                data=buffer,
                file_name="sesion_evaluacion.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
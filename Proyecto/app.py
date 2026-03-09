import os
import io
import json
import tempfile

import streamlit as st
import pandas as pd

from extractor_pdf import procesar_todo_automaticamente
from config import Config, todos_dias

todos_dias = todos_dias
from buscador_evaluacion import buscar_sesion_evaluacion

# ---------------------------------------------------------------------------
# NIVELES DESDE JSON
# ---------------------------------------------------------------------------

def _encontrar_json() -> str:
    """Busca horarios_consolidados.json en ../data/ relativo al script."""
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
    """
    Devuelve (niveles_ordenados, grupos_por_nivel, grupos_por_codigo) del JSON consolidado.
    - grupos_por_nivel:  {nivel: [curso, ...]}
    - grupos_por_codigo: {codigo_profesor: {nivel: [curso, ...]}}
    """
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

def resolver_recreos(profesores: list, sesiones_recreo: list, permitir_recreo: bool) -> set:
    """
    Extrae las horas de inicio reales de las sesiones indicadas en `sesiones_recreo`
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

    # Cada sesión N corresponde al (N-1)-ésimo punto de inicio
    resultado = set()
    for sesion in sesiones_recreo:
        idx = sesion - 1
        if 0 <= idx < len(puntos_ordenados):
            resultado.add(puntos_ordenados[idx])
    return resultado




with st.sidebar:
    st.header("⚙️ Configuración")

    with st.expander("🏫 Nivel y días", expanded=True):
        nivel = st.selectbox(
            "Nivel del grupo",
            options=NIVELES_DISPONIBLES,
        )
        grupos_del_nivel = GRUPOS_POR_NIVEL.get(nivel, [])

        col_cb, col_btn = st.columns([3, 1])
        with col_cb:
            seleccionar_todos_cursos = st.checkbox(
                "Seleccionar todos los cursos",
                value=True,
                key="cb_todos_cursos",
                help="Marca todos por defecto. Luego puedes quitar los que no quieras.",
            )
        with col_btn:
            if st.button("Limpiar", key="btn_limpiar_cursos", help="Deseleccionar todos los cursos"):
                st.session_state["cursos_sel"] = []
                st.rerun()

        # Sincronizar session_state con el checkbox
        if seleccionar_todos_cursos:
            st.session_state["cursos_sel"] = grupos_del_nivel

        if "cursos_sel" not in st.session_state:
            st.session_state["cursos_sel"] = []

        cursos = st.multiselect(
            "Cursos",
            options=grupos_del_nivel,
            default=st.session_state["cursos_sel"],
            help="Puedes añadir o quitar cursos individualmente.",
        )
        st.session_state["cursos_sel"] = cursos
        # TODO Sprint 1: sustituir todos_dias por config.get_dias_nivel(nivel)
        # cuando Lucas tenga inferir_nivel() funcionando
        dias = st.multiselect(
            "Días disponibles para evaluación",
            options=todos_dias,
            default=todos_dias,
        )

    duracion_minutos = st.slider(
        "⏱️ Duración de la reunión (minutos)",
        min_value=30,
        max_value=120,
        value=55,
        step=5,
        help="El buscador encontrará un bloque contiguo libre de al menos esta duración.",
    )
    sesiones_por_dia = 15
    sesiones_recreo = [4, 8, 13]  # Sesiones de recreo hardcodeadas

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
        hora_recreo=sesiones_recreo[0] if sesiones_recreo else 4,
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

    # Preseleccionar profesores que impartan en el nivel y cursos elegidos en el sidebar
    def profesores_del_nivel_y_cursos(nivel_sel, cursos_sel):
        cursos_set = set(cursos_sel)
        preseleccionados = []
        for p in profesores:
            codigo = p["profesor"]["codigo"]
            grupos_prof = GRUPOS_POR_CODIGO.get(codigo, {})
            cursos_prof = set(grupos_prof.get(nivel_sel, []))
            if cursos_prof & cursos_set:  # intersección: da clase en algún curso seleccionado
                preseleccionados.append(
                    p["profesor"].get("nombre", p["profesor"].get("codigo", "SIN_NOMBRE"))
                )
        return preseleccionados

    default_seleccionados = profesores_del_nivel_y_cursos(nivel, cursos)

    col_cb2, col_btn2 = st.columns([3, 1])
    with col_cb2:
        seleccionar_todos_profs = st.checkbox(
            "Seleccionar todos los profesores del nivel",
            value=True,
            key="cb_todos_profs",
            help="Marca todos por defecto. Luego puedes quitar los que no quieras.",
        )
    with col_btn2:
        if st.button("Limpiar", key="btn_limpiar_profs", help="Deseleccionar todos los profesores"):
            st.session_state["profs_sel"] = []
            st.rerun()

    # Sincronizar session_state con el checkbox
    if seleccionar_todos_profs:
        st.session_state["profs_sel"] = default_seleccionados

    if "profs_sel" not in st.session_state:
        st.session_state["profs_sel"] = []

    seleccionados = st.multiselect(
        "Profesores del equipo:",
        options=nombres_disponibles,
        default=st.session_state["profs_sel"],
        help="Preseleccionados según nivel y cursos. Puedes añadir o quitar individualmente.",
    )
    st.session_state["profs_sel"] = seleccionados

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
            recreos = resolver_recreos(profesores, sesiones_recreo, config.permitir_recreo)

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
                    "Sesión más cercana": cercana
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
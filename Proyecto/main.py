from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

try:
    from buscador_evaluacion import Resultado, buscar_sesion_evaluacion
    from config import Config
    from validacion import validate_schedule
    from constants import (
        DEFAULT_PDF_NAME,
        DEFAULT_JSON_NAME,
        DEFAULT_RESULTS_NAME,
        DEFAULT_CONFIG_NAME,
        NIVEL_CONFIG_ALIAS,
        DURACION_MINUTOS,
    )
except ImportError:
    from Proyecto.buscador_evaluacion import Resultado, buscar_sesion_evaluacion
    from Proyecto.config import Config
    from Proyecto.validacion import validate_schedule
    from Proyecto.constants import (
        DEFAULT_PDF_NAME,
        DEFAULT_JSON_NAME,
        DEFAULT_RESULTS_NAME,
        DEFAULT_CONFIG_NAME,
        NIVEL_CONFIG_ALIAS,
        DURACION_MINUTOS,
    )


PROJECT_DIR = Path(__file__).resolve().parent
REPO_DIR = PROJECT_DIR.parent
DATA_DIR = REPO_DIR / "data"
LOGS_DIR = REPO_DIR / "logs"


def get_extractor_dependencies():
    """Carga perezosamente las dependencias del extractor PDF."""
    try:
        import pdfplumber
        from extractor_pdf import procesar_pagina, procesar_todo_automaticamente
    except ImportError:
        import pdfplumber
        from Proyecto.extractor_pdf import procesar_pagina, procesar_todo_automaticamente
    return pdfplumber, procesar_pagina, procesar_todo_automaticamente


def setup_logging(log_path: Path) -> None:
    """Configura logging a fichero y consola para la ejecución CLI."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def parse_args() -> argparse.Namespace:
    """Parsea los argumentos de línea de comandos del orquestador."""
    parser = argparse.ArgumentParser(
        description=(
            "Orquesta la extracción de horarios desde PDF y la búsqueda de "
            "sesiones de evaluación por curso."
        )
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=DATA_DIR / DEFAULT_PDF_NAME,
        help="PDF concreto a procesar. Si no existe, se probará con el JSON consolidado.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Carpeta de datos donde buscar PDFs y guardar artefactos.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DATA_DIR / DEFAULT_CONFIG_NAME,
        help="Ruta del archivo JSON de configuración.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DATA_DIR / DEFAULT_JSON_NAME,
        help="Ruta donde guardar el JSON consolidado de horarios.",
    )
    parser.add_argument(
        "--output-results",
        type=Path,
        default=DATA_DIR / DEFAULT_RESULTS_NAME,
        help="Ruta donde guardar los resultados de evaluación.",
    )
    parser.add_argument(
        "--duracion-minutos",
        type=int,
        default=DURACION_MINUTOS,
        help="Duración mínima de la sesión de evaluación.",
    )
    parser.add_argument(
        "--curso",
        action="append",
        dest="cursos",
        default=None,
        help="Curso concreto a procesar. Se puede repetir.",
    )
    parser.add_argument(
        "--nivel",
        action="append",
        dest="niveles",
        default=None,
        help="Nivel concreto a procesar. Se puede repetir.",
    )
    return parser.parse_args()


def load_config(config_path: Path) -> Config:
    """Carga la configuración desde JSON o devuelve la configuración por defecto."""
    if config_path.is_file():
        logging.info("Cargando configuración desde %s", config_path)
        return Config.cargar(str(config_path))

    logging.info(
        "No se encontró config en %s. Se usará la configuración por defecto.",
        config_path,
    )
    return Config()


def extract_single_pdf(pdf_path: Path) -> List[dict]:
    """Extrae horarios válidos de un único PDF."""
    pdfplumber, procesar_pagina, _ = get_extractor_dependencies()
    horarios: List[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            raise ValueError(f"El PDF está vacío: {pdf_path}")

        logging.info("Procesando %s (%s páginas)", pdf_path.name, len(pdf.pages))
        for index, page in enumerate(pdf.pages, start=1):
            try:
                horario = procesar_pagina(page)
                errores = validate_schedule(horario)
                if errores:
                    logging.warning(
                        "Página %s descartada en %s: %s",
                        index,
                        pdf_path.name,
                        "; ".join(errores),
                    )
                    continue
                horarios.append(horario)
            except Exception as exc:  # pragma: no cover - ruta defensiva
                logging.exception(
                    "Error procesando la página %s de %s: %s",
                    index,
                    pdf_path.name,
                    exc,
                )
    return horarios


def load_horarios_from_json(json_path: Path) -> List[dict]:
    """Carga horarios consolidados desde JSON."""
    with json_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"El archivo {json_path} no contiene una lista de horarios.")
    return data


def save_json(data: object, output_path: Path) -> None:
    """Guarda un objeto JSON serializable con indentación legible."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def get_horarios(args: argparse.Namespace) -> List[dict]:
    """Obtiene horarios desde un PDF concreto, desde una carpeta o desde JSON."""
    pdf_path = args.pdf
    data_dir = args.data_dir
    output_json = args.output_json

    if pdf_path.is_file():
        horarios = extract_single_pdf(pdf_path)
        save_json(horarios, output_json)
        logging.info("JSON consolidado guardado en %s", output_json)
        return horarios

    pdfs_in_dir = sorted(data_dir.glob("*.pdf"))
    if pdfs_in_dir:
        _, _, procesar_todo_automaticamente = get_extractor_dependencies()
        logging.info(
            "No existe el PDF %s; se procesarán %s PDFs de %s",
            pdf_path,
            len(pdfs_in_dir),
            data_dir,
        )
        horarios = procesar_todo_automaticamente(str(data_dir))
        save_json(horarios, output_json)
        logging.info("JSON consolidado guardado en %s", output_json)
        return horarios

    if output_json.is_file():
        logging.info("Usando JSON consolidado existente en %s", output_json)
        return load_horarios_from_json(output_json)

    raise FileNotFoundError(
        "No se encontró un PDF de entrada ni un JSON consolidado para continuar."
    )


def normalizar_nivel_para_config(nivel: str) -> str:
    """Normaliza etiquetas de nivel para consultar la configuración."""
    return NIVEL_CONFIG_ALIAS.get(nivel, nivel)


def collect_courses(
    horarios: Iterable[dict],
    niveles_filtrados: Optional[Set[str]] = None,
    cursos_filtrados: Optional[Set[str]] = None,
) -> Dict[Tuple[str, str], Set[str]]:
    """Construye el índice nivel/curso -> códigos de profesor."""
    courses_map: Dict[Tuple[str, str], Set[str]] = {}
    for horario in horarios:
        codigo = horario.get("profesor", {}).get("codigo")
        if not codigo:
            continue

        grupos = horario.get("grupos", {})
        if not isinstance(grupos, dict):
            continue

        for nivel, cursos in grupos.items():
            if niveles_filtrados and nivel not in niveles_filtrados:
                continue
            if not isinstance(cursos, list):
                continue
            for curso in cursos:
                if cursos_filtrados and curso not in cursos_filtrados:
                    continue
                courses_map.setdefault((nivel, curso), set()).add(codigo)
    return dict(sorted(courses_map.items()))


def resultado_to_dict(nivel: str, curso: str, resultado: Resultado) -> dict:
    """Serializa el resultado del buscador a un diccionario JSON-friendly."""
    return {
        "nivel": nivel,
        "curso": curso,
        "sin_solucion": resultado.sin_solucion,
        "dia": resultado.dia,
        "hora_inicio": resultado.hora_inicio,
        "hora_fin": resultado.hora_fin,
        "coste_total": resultado.coste_total,
        "peor_penalizacion": resultado.peor_penalizacion,
        "es_recreo": resultado.es_recreo,
        "es_septima": resultado.es_septima,
        "explicacion": resultado.explicacion,
        "diagnostico_bloqueadores": [
            {"profesor": profesor, "slots_bloqueados": slots}
            for profesor, slots in resultado.diagnostico_bloqueadores
        ],
        "detalle": [
            {
                "codigo": detalle.codigo,
                "nombre": detalle.nombre,
                "penalizacion": detalle.penalizacion,
                "sesion_mas_cercana": (
                    {
                        "inicio": detalle.sesion_ocupada_mas_cercana[0],
                        "fin": detalle.sesion_ocupada_mas_cercana[1],
                    }
                    if detalle.sesion_ocupada_mas_cercana
                    else None
                ),
                "tiene_eventos_ese_dia": detalle.tiene_eventos_ese_dia,
            }
            for detalle in resultado.detalle
        ],
    }


def run_scheduler(
    horarios: List[dict],
    config: Config,
    duracion_minutos: int,
    niveles_filtrados: Optional[Set[str]] = None,
    cursos_filtrados: Optional[Set[str]] = None,
) -> List[dict]:
    """Ejecuta la búsqueda de sesiones de evaluación para todos los cursos detectados."""
    course_map = collect_courses(horarios, niveles_filtrados, cursos_filtrados)
    if not course_map:
        logging.warning("No se encontraron cursos para procesar.")
        return []

    logging.info("Cursos detectados para evaluación: %s", len(course_map))
    resultados_previos: Dict[str, Resultado] = {}
    resultados_serializados: List[dict] = []

    for (nivel, curso), equipo_codigos in course_map.items():
        nivel_config = normalizar_nivel_para_config(nivel)
        dias_disponibles = config.get_dias_nivel(nivel_config)
        logging.info(
            "Procesando %s/%s con %s profesores. Días candidatos: %s",
            nivel,
            curso,
            len(equipo_codigos),
            ", ".join(dias_disponibles),
        )

        t0 = time.perf_counter()
        resultado = buscar_sesion_evaluacion(
            profesores=horarios,
            equipo_codigos=equipo_codigos,
            config=config,
            dias_disponibles=dias_disponibles,
            duracion_minutos=duracion_minutos,
            resultados_previos=resultados_previos,
        )
        elapsed = time.perf_counter() - t0

        if resultado.sin_solucion:
            logging.info(
                "Sin solución para %s/%s tras %.3fs",
                nivel,
                curso,
                elapsed,
            )
        else:
            logging.info(
                "Slot elegido para %s/%s: %s %s-%s, peso total=%s, peor=%s, tiempo=%.3fs",
                nivel,
                curso,
                resultado.dia,
                resultado.hora_inicio,
                resultado.hora_fin,
                resultado.coste_total,
                resultado.peor_penalizacion,
                elapsed,
            )

        resultados_previos[f"{nivel}|{curso}"] = resultado
        resultados_serializados.append(resultado_to_dict(nivel, curso, resultado))

    return resultados_serializados


def main() -> int:
    """Punto de entrada CLI del orquestador completo del proyecto."""
    args = parse_args()
    setup_logging(LOGS_DIR / "app.log")

    try:
        config = load_config(args.config)
        horarios = get_horarios(args)
        if not horarios:
            logging.error("No se obtuvo ningún horario válido.")
            return 1

        logging.info("Horarios válidos disponibles: %s", len(horarios))
        resultados = run_scheduler(
            horarios=horarios,
            config=config,
            duracion_minutos=args.duracion_minutos,
            niveles_filtrados=set(args.niveles) if args.niveles else None,
            cursos_filtrados=set(args.cursos) if args.cursos else None,
        )

        save_json(resultados, args.output_results)
        logging.info("Resultados guardados en %s", args.output_results)

        print(json.dumps(resultados[:5], ensure_ascii=False, indent=2))
        if len(resultados) > 5:
            print(f"... {len(resultados) - 5} resultados más")
        return 0
    except Exception as exc:  # pragma: no cover - ruta defensiva
        logging.exception("Error inesperado en el orquestador: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

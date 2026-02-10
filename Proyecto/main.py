import json
import pdfplumber  # Necesitamos esto para abrir el archivo
from pathlib import Path
# Importamos la función que SÍ existe
from extractor_pdf import procesar_pagina
from validacion import validate_schedule


def resolve_pdf_path(filename: str = "HORARIO.pdf") -> Path:
    return Path(__file__).resolve().parent / "data" / filename


def print_validation(errors: list[str]) -> None:
    if errors:
        print("\n=== VALIDACIÓN: ERRORES ===")
        for err in errors:
            print(f"- {err}")
    else:
        print("\n=== VALIDACIÓN: OK ===")


def extract_single_pdf(file_path: Path):
    with pdfplumber.open(file_path) as pdf:
        if not pdf.pages:
            raise ValueError("El PDF está vacío.")

        # Asumimos que el horario está en la primera página
        # Si hay más, podrías iterar sobre pdf.pages
        print(f"Procesando: {file_path.name}")
        return procesar_pagina(pdf.pages[0])


def main() -> int:
    pdf_file_path = resolve_pdf_path()

    if not pdf_file_path.exists():
        # Intentamos buscar en la carpeta superior si falló la primera
        # Esto es útil si ejecutas desde 'tests/' o 'Proyecto/'
        pdf_file_path = Path(__file__).resolve().parent.parent / "data" / "HORARIO.pdf"

        if not pdf_file_path.exists():
            print(f"Error: No se encontró el PDF en: {pdf_file_path}")
            return 1

    try:
        # 1. Extracción
        schedule = extract_single_pdf(pdf_file_path)

        # 2. Imprimir resultado JSON
        print(json.dumps(schedule, ensure_ascii=False, indent=2))

        # 3. Validación
        errors = validate_schedule(schedule)
        print_validation(errors)

    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
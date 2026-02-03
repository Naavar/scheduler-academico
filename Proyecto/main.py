import json
from pathlib import Path

from Proyecto.extractor_pdf import extract_schedule
from Proyecto.validacion import validate_schedule


def resolve_pdf_path(filename: str = "HORARIO.pdf") -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / "data" / filename


def print_validation(errors: list[str]) -> None:
    if errors:
        print("\n=== VALIDACIÓN: ERRORES ===")
        for err in errors:
            print("-", err)
    else:
        print("\n=== VALIDACIÓN: OK ===")


def main() -> int:
    pdf_file_path = resolve_pdf_path()

    if not pdf_file_path.exists():
        raise FileNotFoundError(
            f"No se encontró el PDF en: {pdf_file_path}\n"
            "Comprueba que existe 'data/HORARIO.pdf' en la raíz del proyecto."
        )

    schedule = extract_schedule(str(pdf_file_path))

    print(json.dumps(schedule, ensure_ascii=False, indent=2))

    errors = validate_schedule(schedule)
    print_validation(errors)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

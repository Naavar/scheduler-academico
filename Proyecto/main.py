import json
from pathlib import Path

from Proyecto.extractor_pdf import extract_schedule

DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]


def hhmm_to_minutes(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def validate_schedule(data: dict) -> list[str]:
    errors: list[str] = []

    # Profesor
    prof = data.get("profesor", {})
    if not prof.get("nombre"):
        errors.append("Falta profesor.nombre")
    if not prof.get("codigo"):
        errors.append("Falta profesor.codigo")

    # Eventos
    eventos = data.get("eventos")
    if not isinstance(eventos, list) or len(eventos) == 0:
        errors.append("No hay eventos (eventos está vacío o no es lista)")
        return errors

    for i, e in enumerate(eventos):
        dia = e.get("dia")
        ini = e.get("inicio")
        fin = e.get("fin")

        if dia not in DAY_NAMES:
            errors.append(f"Evento {i}: dia inválido: {dia}")
        if not ini or not fin:
            errors.append(f"Evento {i}: falta inicio/fin")
            continue

        try:
            mi = hhmm_to_minutes(ini)
            mf = hhmm_to_minutes(fin)
            if mf <= mi:
                errors.append(f"Evento {i}: fin <= inicio ({ini}–{fin})")
        except Exception:
            errors.append(f"Evento {i}: formato hora inválido ({ini}, {fin})")

        if not e.get("titulo"):
            errors.append(f"Evento {i}: falta titulo")

    return errors


def resolve_pdf_path() -> Path:
    """
    Devuelve la ruta ABSOLUTA al PDF de horarios, independiente del working directory.

    Estructura esperada:
      D:\\Proyecto_Horarios\\
        data\\HORARIO.pdf
        Proyecto\\main.py
    """
    repo_root = Path(__file__).resolve().parent.parent  # ...\\Proyecto_Horarios
    pdf_path = repo_root / "data" / "HORARIO.pdf"
    return pdf_path


if __name__ == "__main__":
    pdf_path = resolve_pdf_path()

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"No se encontró el PDF en: {pdf_path}\n"
            f"Comprueba que existe 'data/HORARIO.pdf' en la raíz del proyecto."
        )

    data = extract_schedule(str(pdf_path))

    # 1) Imprimir JSON (para inspección)
    print(json.dumps(data, ensure_ascii=False, indent=2))

    # 2) Validación
    errs = validate_schedule(data)
    if errs:
        print("\n=== VALIDACIÓN: ERRORES ===")
        for e in errs:
            print("-", e)
    else:
        print("\n=== VALIDACIÓN: OK ===")

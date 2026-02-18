import json
import pdfplumber  # Necesitamos esto para abrir el archivo
from pathlib import Path
# Importamos la función que SÍ existe
from extractor_pdf import procesar_pagina
from validacion import validate_schedule


def resolve_pdf_path(filename: str = "HORARIOS_25_26 - Docentes_anon.pdf") -> Path:
    return Path(__file__).resolve().parent / "data" / filename


def print_validation(errors: list[str]) -> None:
    if errors:
        print("\n=== VALIDACIÓN: ERRORES ===")
        for err in errors:
            print(f"- {err}")
    else:
        print("\n=== VALIDACIÓN: OK ===")


def extract_all_pages_from_pdf(file_path: Path):
    """Extrae todos los horarios de un PDF multipágina"""
    horarios = []
    with pdfplumber.open(file_path) as pdf:
        if not pdf.pages:
            raise ValueError("El PDF está vacío.")

        print(f"📄 Procesando {len(pdf.pages)} páginas de: {file_path.name}")
        for i, page in enumerate(pdf.pages, 1):
            try:
                horario = procesar_pagina(page)
                errores = validate_schedule(horario)
                
                if errores:
                    print(f"  ⚠️ Pág {i}: DESCARTADA - {len(errores)} errores")
                else:
                    horarios.append(horario)
                    print(f"  ✓ Pág {i}: {horario['profesor']['nombre']} ({horario['profesor']['codigo']})")
            except Exception as e:
                print(f"  ❌ Pág {i}: Error - {str(e)}")
    
    return horarios


def main() -> int:
    pdf_file_path = resolve_pdf_path()

    if not pdf_file_path.exists():
        pdf_file_path = Path(__file__).resolve().parent.parent / "data" / "HORARIOS_25_26 - Docentes_anon.pdf"

        if not pdf_file_path.exists():
            print(f"❌ Error: No se encontró el PDF en: {pdf_file_path}")
            return 1

    try:
        # Extraer todos los horarios del PDF
        horarios = extract_all_pages_from_pdf(pdf_file_path)
        
        if not horarios:
            print("\n⚠️ No se extrajo ningún horario válido.")
            return 1
        
        # Guardar resultado consolidado
        output_path = pdf_file_path.parent / "horarios_consolidados.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(horarios, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Éxito: {len(horarios)} horarios extraídos")
        print(f"💾 Guardado en: {output_path}")
        
        # Mostrar resumen
        print("\n📊 Resumen:")
        for h in horarios[:5]:  # Mostrar solo los primeros 5
            print(f"  - {h['profesor']['nombre']} ({h['profesor']['codigo']}): {len(h['eventos'])} eventos")
        if len(horarios) > 5:
            print(f"  ... y {len(horarios) - 5} más")

    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
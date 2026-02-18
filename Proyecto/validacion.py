from __future__ import annotations
import re
from typing import Any, List, Dict

# Constantes
DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
REGEX_HORA = r"^\d{1,2}:\d{2}$"  # Acepta "9:00" y "09:00"


def hhmm_to_minutes(hhmm: str) -> int:
    """Convierte HH:MM a minutos totales."""
    try:
        hours, minutes = map(int, hhmm.split(":"))
        return hours * 60 + minutes
    except ValueError:
        return -1  # Retorno de error seguro


def validate_schedule(schedule: Dict[str, Any]) -> List[str]:
    """
    Valida un objeto horario completo.
    Retorna una lista de errores (vacía si es válido).
    """
    errors: List[str] = []

    # 1. Validar Profesor
    prof = schedule.get("profesor", {})
    if not isinstance(prof, dict):
        errors.append("La clave 'profesor' debe ser un objeto")
        return errors  # Error crítico, paramos aquí

    nombre = prof.get("nombre", "")
    codigo = prof.get("codigo", "")
    
    # Aceptar nombres anonimizados (Profesor XXX) y códigos sintéticos (PROFXXX)
    if not nombre or nombre == "Desconocido":
        errors.append("Falta nombre del profesor válido")
    if not codigo or codigo == "N/A":
        # Solo advertencia si el nombre es válido (puede ser anonimizado)
        if nombre and nombre != "Desconocido":
            pass  # Permitir códigos sintéticos
        else:
            errors.append("Falta código del profesor válido")

    # 2. Validar Eventos
    events = schedule.get("eventos")
    if not isinstance(events, list):
        errors.append("'eventos' debe ser una lista")
        return errors

    if not events:
        errors.append("Advertencia: La lista de eventos está vacía")

    for idx, event in enumerate(events):
        day = event.get("dia")
        start = event.get("inicio")
        end = event.get("fin")
        asignatura = event.get("asignatura")

        # Validar Día
        if day not in DAY_NAMES:
            errors.append(f"Evento {idx}: día inválido '{day}'")

        # Validar Asignatura
        if not asignatura:
            errors.append(f"Evento {idx}: falta asignatura")

        # Validar Horas
        if not start or not end:
            errors.append(f"Evento {idx}: falta hora inicio/fin")
            continue

        # Chequeo de formato con Regex (más flexible)
        if not re.match(REGEX_HORA, str(start)) or not re.match(REGEX_HORA, str(end)):
            errors.append(f"Evento {idx}: formato hora inválido ({start} - {end})")
            continue

        # Chequeo lógico (Fin > Inicio)
        start_min = hhmm_to_minutes(str(start))
        end_min = hhmm_to_minutes(str(end))

        if start_min == -1 or end_min == -1:
            errors.append(f"Evento {idx}: horas no numéricas")
        elif end_min <= start_min:
            errors.append(f"Evento {idx}: fin <= inicio ({start} - {end})")

    return errors
from __future__ import annotations

from typing import Any

DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]


def hhmm_to_minutes(hhmm: str) -> int:
    hours, minutes = map(int, hhmm.split(":"))
    return hours * 60 + minutes


def validate_schedule(schedule: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    prof = schedule.get("profesor", {}) or {}
    if not prof.get("nombre"):
        errors.append("Falta profesor.nombre")
    if not prof.get("codigo"):
        errors.append("Falta profesor.codigo")

    events = schedule.get("eventos")
    if not isinstance(events, list) or not events:
        errors.append("No hay eventos (eventos está vacío o no es lista)")
        return errors

    for idx, event in enumerate(events):
        day = event.get("dia")
        start = event.get("inicio")
        end = event.get("fin")

        if day not in DAY_NAMES:
            errors.append(f"Evento {idx}: dia inválido: {day}")

        if not start or not end:
            errors.append(f"Evento {idx}: falta inicio/fin")
            continue

        try:
            start_min = hhmm_to_minutes(start)
            end_min = hhmm_to_minutes(end)
            if end_min <= start_min:
                errors.append(f"Evento {idx}: fin <= inicio ({start}–{end})")
        except ValueError:
            errors.append(f"Evento {idx}: formato hora inválido ({start}, {end})")

        if not event.get("titulo"):
            errors.append(f"Evento {idx}: falta titulo")

    return errors

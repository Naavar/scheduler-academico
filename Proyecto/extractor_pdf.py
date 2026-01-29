# Extracción de horarios (rejilla mañana/tarde) desde PDF con texto seleccionable.
# Salida: JSON estructurado con eventos (día, inicio, fin, turno, titulo) + validación básica.

from __future__ import annotations
from pathlib import Path
import re
from typing import Dict, List, Tuple, Any, Optional

import pdfplumber

PDF_PATH_DEFAULT = str(Path(__file__).resolve().parent.parent / "data" / "HORARIO.pdf")

DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")

# Patrones auxiliares
CODE_RE = re.compile(r"^\d{4}~[A-Z0-9]+$")
ROOM_RE = re.compile(r"^[A-Z]\d{2}$")


# -----------------------------
# Utilidades básicas
# -----------------------------

def parse_teacher_header(text: str) -> Dict[str, Optional[str]]:
    """
    Extrae:
      'APELLIDOS, NOMBRE (codigo)' -> {"nombre": "...", "codigo": "..."}
    """
    m = re.search(r"([A-ZÁÉÍÓÚÑ,\s]+)\s+\(([^)]+)\)", text or "")
    if not m:
        return {"nombre": None, "codigo": None}
    return {"nombre": m.group(1).strip(), "codigo": m.group(2).strip()}


def word_center_x(w: Dict[str, Any]) -> float:
    return (w["x0"] + w["x1"]) / 2.0


def normalize_text(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip()).upper()

    # Reparación específica para grupos con '~':
    # "BIG-D~BIGD- C03" -> "BIG-D~BIGDC03"
    s = re.sub(r"(~[A-Z0-9-]+)-\s+([A-Z0-9]{2,})\b", r"\1\2", s)

    return s


def fix_split_group_codes(s: str) -> str:
    """
    Repara casos donde el PDF parte códigos de grupo tras '~' en dos tokens:
      "BIG-D~BIGD- C03" -> "BIG-D~BIGDC03"
    Aplica solo cuando hay '~', para no romper "RDP - DPTO INF".
    """
    if "~" not in s:
        return s

    # Caso: ...~XXXX- C03  (guion pegado al token anterior)
    s = re.sub(r"(~[A-Z0-9-]{2,})-\s+([A-Z0-9]{2,})\b", r"\1\2", s)

    # Caso: ...~XXXX - C03 (guion separado por espacios)
    s = re.sub(r"(~[A-Z0-9-]{2,})\s*-\s+([A-Z0-9]{2,})\b", r"\1\2", s)

    return s


# -----------------------------
# Días (columnas) y horas (ticks)
# -----------------------------

def compute_day_bounds(words: List[Dict[str, Any]]) -> List[Tuple[str, float, float]]:
    """
    Calcula límites X por cada día (L..V) usando la posición de las cabeceras.
    Devuelve [(dia, x_left, x_right), ...]
    """
    day_x: Dict[str, float] = {}
    for w in words:
        if w.get("text") in DAY_NAMES:
            day_x[w["text"]] = word_center_x(w)

    if len(day_x) != 5:
        raise ValueError(f"No se han encontrado las 5 cabeceras de días. Encontradas: {day_x}")

    bounds: List[Tuple[str, float, float]] = []
    for i, d in enumerate(DAY_NAMES):
        cx = day_x[d]
        if i == 0:
            left = -1e9
            right = (cx + day_x[DAY_NAMES[i + 1]]) / 2.0
        elif i == len(DAY_NAMES) - 1:
            left = (day_x[DAY_NAMES[i - 1]] + cx) / 2.0
            right = 1e9
        else:
            left = (day_x[DAY_NAMES[i - 1]] + cx) / 2.0
            right = (cx + day_x[DAY_NAMES[i + 1]]) / 2.0
        bounds.append((d, left, right))

    return bounds


def assign_day(day_bounds: List[Tuple[str, float, float]], w: Dict[str, Any]) -> Optional[str]:
    cx = word_center_x(w)
    for day, left, right in day_bounds:
        if left <= cx < right:
            return day
    return None


def extract_time_ticks(words: List[Dict[str, Any]], x_left_max: float = 90.0) -> List[Tuple[float, str]]:
    """
    Extrae ticks de horas (columna izquierda).
    Devuelve [(y_top, 'HH:MM'), ...] ordenados por y.
    """
    ticks: List[Tuple[float, str]] = []
    for w in words:
        t = (w.get("text") or "").strip()
        if TIME_RE.match(t) and w["x0"] < x_left_max:
            ticks.append((w["top"], t))
    ticks.sort(key=lambda x: x[0])
    return ticks


def split_ticks_into_grids(
        time_ticks: List[Tuple[float, str]],
        big_gap: float = 90.0
) -> List[List[Tuple[float, str]]]:
    """
    Separa ticks en rejillas (normalmente mañana y tarde) por saltos grandes en Y.
    """
    time_ticks = sorted(time_ticks, key=lambda x: x[0])
    grids: List[List[Tuple[float, str]]] = []
    cur: List[Tuple[float, str]] = []
    for y, t in time_ticks:
        if not cur:
            cur = [(y, t)]
        elif (y - cur[-1][0]) > big_gap:
            grids.append(cur)
            cur = [(y, t)]
        else:
            cur.append((y, t))
    if cur:
        grids.append(cur)
    return grids


def dedup_grid_ticks(grid_ticks: List[Tuple[float, str]], min_y_sep: float = 1.0) -> List[Tuple[float, str]]:
    """
    Dedup dentro de una rejilla:
      - elimina duplicados exactos muy cercanos
      - y se queda con el primer tick por hora si se repite en esa rejilla
    """
    grid_ticks = sorted(grid_ticks, key=lambda x: x[0])
    out: List[Tuple[float, str]] = []
    for y, t in grid_ticks:
        if not out:
            out.append((y, t))
            continue
        y_prev, t_prev = out[-1]
        if abs(y - y_prev) < min_y_sep and t == t_prev:
            continue
        out.append((y, t))

    seen = set()
    out2: List[Tuple[float, str]] = []
    for y, t in out:
        if t in seen:
            continue
        out2.append((y, t))
        seen.add(t)
    return out2


def grid_y_limits(grid_ticks: List[Tuple[float, str]], margin: float = 25.0) -> Tuple[float, float]:
    ys = [y for y, _ in grid_ticks]
    return min(ys) - margin, max(ys) + margin


def build_slots_from_ticks(grid_ticks: List[Tuple[float, str]]) -> List[Dict[str, Any]]:
    """
    Crea slots consecutivos a partir de ticks.
    """
    grid_ticks = sorted(grid_ticks, key=lambda x: x[0])
    slots: List[Dict[str, Any]] = []
    for i in range(len(grid_ticks) - 1):
        y0, t0 = grid_ticks[i]
        y1, t1 = grid_ticks[i + 1]
        slots.append({"t_ini": t0, "t_fin": t1, "y_top": y0, "y_bottom": y1})
    return slots


# -----------------------------
# Extracción de texto por slot
# -----------------------------

def is_noise(w: Dict[str, Any]) -> bool:
    txt = (w.get("text") or "").strip()
    if TIME_RE.match(txt):
        return True
    if txt in DAY_NAMES:
        return True
    if txt in {"Horario", "semanal:", "Profesores"}:
        return True
    if txt.isdigit() and len(txt) <= 2:
        return True
    return False


def word_in_slot(w: Dict[str, Any], slot: Dict[str, Any]) -> bool:
    """
    Criterio: centro vertical dentro del slot.
    """
    cy = (w["top"] + w["bottom"]) / 2.0
    return slot["y_top"] <= cy < slot["y_bottom"]


def extract_slot_texts(
        words: List[Dict[str, Any]],
        day_bounds: List[Tuple[str, float, float]],
        slots: List[Dict[str, Any]],
        y_min: float,
        y_max: float,
) -> Dict[str, List[str]]:
    """
    Devuelve por día una lista de textos (uno por slot). Texto normalizado.
    """
    out: Dict[str, List[str]] = {d: [""] * len(slots) for d, _, _ in day_bounds}

    day_words: List[Tuple[str, Dict[str, Any]]] = []
    for w in words:
        if is_noise(w):
            continue
        if w["top"] < y_min or w["top"] > y_max:
            continue
        day = assign_day(day_bounds, w)
        if day is None:
            continue
        day_words.append((day, w))

    for day in out:
        ws = [word for d, word in day_words if d == day]

        for i, slot in enumerate(slots):
            in_slot = [w for w in ws if word_in_slot(w, slot)]

            if not in_slot:
                continue

            in_slot.sort(key=lambda word: (word["top"], word["x0"]))
            text = " ".join(word["text"] for word in in_slot)

            norm = normalize_text(text)
            out[day][i] = norm

    return out


def determine_turno(hora_inicio: str) -> str:
    """
    Determina si un slot es de mañana o tarde basándose en la hora de inicio.
    Asume que la tarde comienza a partir de las 15:00.
    """
    try:
        h, m = map(int, hora_inicio.split(":"))
        hora_decimal = h + m / 60.0
        return "tarde" if hora_decimal >= 15.0 else "mañana"
    except (ValueError, AttributeError):
        return "mañana"  # fallback


def merge_consecutive(
        day_slot_texts: Dict[str, List[str]],
        slots: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Fusiona slots consecutivos del mismo día cuando el texto es exactamente igual.
    """
    eventos: List[Dict[str, Any]] = []
    for day, arr in day_slot_texts.items():
        i = 0
        while i < len(arr):
            if not arr[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(arr) and arr[j + 1] == arr[i]:
                j += 1

            # Determinar el turno basándose en la hora de inicio
            turno_real = determine_turno(slots[i]["t_ini"])

            eventos.append(
                {
                    "dia": day,
                    "turno": turno_real,
                    "inicio": slots[i]["t_ini"],
                    "fin": slots[j]["t_fin"],
                    "titulo": arr[i],
                }
            )
            i = j + 1
    return eventos


# -----------------------------
# Limpieza: unir "continuaciones" de una misma celda
# -----------------------------

def looks_like_room(s: str) -> bool:
    s = (s or "").strip().upper()
    if ROOM_RE.match(s):
        return True
    if re.match(r"^[A-Z]\d{2},", s):  # "B23, INF.SAI..."
        return True
    return False


def looks_like_code(s: str) -> bool:
    return bool(CODE_RE.match((s or "").strip().upper()))


def looks_like_groups(s: str) -> bool:
    s = (s or "").strip().upper()
    if not re.search(r"\b[A-Z0-9-]{1,12}~[A-Z0-9-]{1,12}\b", s):
        return False
    non_group_words = [w for w in re.findall(r"[A-ZÁÉÍÓÚÑ]{4,}", s) if "~" not in w]
    return len(non_group_words) <= 1


def _is_major_activity_title(t: str) -> bool:
    t = (t or "").strip().upper()
    return any(k in t for k in [
        "DESARROLLO WEB", "PROGRAMACIÓN", "MONTAJE Y MANTENIMIENTO",
        "GUARDIA", "REUNIÓN", "REUNION"
    ])


def _is_short_complement(t: str) -> bool:
    t = (t or "").strip().upper()
    if looks_like_room(t) or looks_like_code(t) or looks_like_groups(t):
        return True
    # detalle breve tipo "RDP - DPTO INF"
    return len(t) <= 28 and ("-" in t)


def merge_continuations(eventos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Une eventos adyacentes SOLO si el segundo es un complemento corto.
    Evita mezclar reunión con clases, o clases distintas entre sí.
    """
    eventos = sorted(eventos, key=lambda ev: (ev["dia"], ev["turno"], ev["inicio"]))
    out: List[Dict[str, Any]] = []

    for e in eventos:
        if not out:
            out.append(e)
            continue

        prev = out[-1]

        if e["dia"] != prev["dia"] or e["turno"] != prev["turno"] or e["inicio"] != prev["fin"]:
            out.append(e)
            continue

        t_prev = (prev.get("titulo") or "").strip().upper()
        t_cur = (e.get("titulo") or "").strip().upper()

        # Nunca mezclar recreo
        if t_prev == "RECREO" or t_cur == "RECREO":
            out.append(e)
            continue

        # Reunión: solo complemento corto no "principal"
        if "REUNIÓN" in t_prev or "REUNION" in t_prev:
            if _is_short_complement(t_cur) and not _is_major_activity_title(t_cur):
                prev["titulo"] = (prev["titulo"] + " / " + e["titulo"]).strip()
                prev["fin"] = e["fin"]
                continue
            out.append(e)
            continue

        # Guardia: permite complemento corto
        if "GUARDIA" in t_prev:
            if _is_short_complement(t_cur) and not _is_major_activity_title(t_cur):
                prev["titulo"] = (prev["titulo"] + " " + e["titulo"]).strip()
                prev["fin"] = e["fin"]
                continue
            out.append(e)
            continue

        # Lectiva u otras: solo si es complemento corto no principal
        if _is_short_complement(t_cur) and not _is_major_activity_title(t_cur):
            prev["titulo"] = (prev["titulo"] + " " + e["titulo"]).strip()
            prev["fin"] = e["fin"]
            continue

        out.append(e)

    return out


def filter_events(eventos: List[Dict[str, Any]], drop_recreo: bool = True) -> List[Dict[str, Any]]:
    if not drop_recreo:
        return eventos
    return [e for e in eventos if (e.get("titulo") or "").strip().upper() != "RECREO"]


def fix_titles(eventos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Reparación final de títulos:
    - Une patrones tipo "~BIGD- C03" -> "~BIGDC03" (por seguridad).
    - Elimina guion colgante al final de un token de grupo "~XXXX-" -> "~XXXX"
      (caso: el PDF dejó el sufijo en otro slot, pero si no está, no queremos un '-' colgando).
    """
    for e in eventos:
        t = (e.get("titulo") or "").strip()

        # 1) unión típica
        t = re.sub(r"(~[A-Z0-9-]+)-\s+([A-Z0-9]{2,})\b", r"\1\2", t)

        # 2) guion colgante justo antes de fin de string
        #    "... BIG-D~BIGD-" -> "... BIG-D~BIGD"
        t = re.sub(r"(~[A-Z0-9-]+)-\b(?=\s*$)", r"\1", t)

        e["titulo"] = t
    return eventos


# -----------------------------
# API principal del extractor
# -----------------------------

def extract_schedule(pdf_path: str = PDF_PATH_DEFAULT) -> Dict[str, Any]:
    """
    Función principal: devuelve dict listo para serializar a JSON:
      {"profesor": {...}, "eventos": [...]}
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]

        full_text = page.extract_text() or ""
        teacher = parse_teacher_header(full_text)

        words = page.extract_words(
            keep_blank_chars=False,
            use_text_flow=True,
            extra_attrs=["size", "fontname"],
        )

        day_bounds = compute_day_bounds(words)
        time_ticks = extract_time_ticks(words)

        grids = split_ticks_into_grids(time_ticks, big_gap=90.0)

        eventos: List[Dict[str, Any]] = []
        for idx, g in enumerate(grids[:2]):  # normalmente 2: mañana/tarde
            g2 = dedup_grid_ticks(g)
            if len(g2) < 2:
                continue

            y_min, y_max = grid_y_limits(g2)
            slots = build_slots_from_ticks(g2)

            day_slot_texts = extract_slot_texts(words, day_bounds, slots, y_min, y_max)
            eventos.extend(merge_consecutive(day_slot_texts, slots))

    # Limpieza post-proceso (orden importante)
    eventos = filter_events(eventos, drop_recreo=True)  # primero fuera recreos
    eventos = merge_continuations(eventos)  # luego fusiones seguras
    eventos = filter_events(eventos, drop_recreo=True)  # blindaje
    eventos = fix_titles(eventos)
    return {"profesor": teacher, "eventos": eventos}

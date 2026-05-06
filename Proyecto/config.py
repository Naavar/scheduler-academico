from dataclasses import dataclass, field, asdict
import json
try:
    from Proyecto.constants import (
        DIAS_VALIDOS,
        SESIONES_POR_DIA,
        RECREOS_DEFAULT,
        SEPTIMA_HORA_IDX,
        MAX_SESIONES_POR_DIA,
    )
except ImportError:
    from constants import (
        DIAS_VALIDOS,
        SESIONES_POR_DIA,
        RECREOS_DEFAULT,
        SEPTIMA_HORA_IDX,
        MAX_SESIONES_POR_DIA,
    )

todos_dias = DIAS_VALIDOS  # alias de compatibilidad para otros módulos que importen esto


@dataclass
class Config:
    recreos: list = field(default_factory=lambda: RECREOS_DEFAULT.copy())
    sesiones_por_dia: int = SESIONES_POR_DIA
    septima_hora_idx: int = SEPTIMA_HORA_IDX
    permitir_septima_hora: bool = False
    permitir_recreo: bool = False
    permitir_horas_no_obligatorias: bool = False
    dias_disponibles_por_nivel: dict = field(default_factory=dict)

    def __post_init__(self):
        if not (1 <= self.sesiones_por_dia <= MAX_SESIONES_POR_DIA):
            raise ValueError(
                f"sesiones_por_dia={self.sesiones_por_dia} debe estar entre 1 y {MAX_SESIONES_POR_DIA}"
            )

    def get_dias_nivel(self, nivel: str) -> list[str]:
        return self.dias_disponibles_por_nivel.get(nivel, todos_dias)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "Config":
        return cls.from_dict(json.loads(json_str))

    def guardar(self, ruta: str) -> None:
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def cargar(cls, ruta: str) -> "Config":
        with open(ruta, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())
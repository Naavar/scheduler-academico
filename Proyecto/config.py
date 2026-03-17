from dataclasses import dataclass, field, asdict
import json
from constants import (
    DIAS_VALIDOS,
    HORA_RECREO,
    SESIONES_POR_DIA,
    MAX_SESIONES_POR_DIA,
)

@dataclass
class Config:
    horas_recreo: list = field(default_factory=lambda: [4, 9, 13])
    sesiones_por_dia: int = 16
    permitir_septima_hora: bool = False
    permitir_recreo: bool = False
    permitir_horas_no_obligatorias: bool = False
    dias_disponibles_por_nivel: dict = field(default_factory=dict)

    def __post_init__(self):
        if not (1 <= self.sesiones_por_dia <= 20):
            raise ValueError(
                f"sesiones_por_dia={self.sesiones_por_dia} debe estar entre 1 y {MAX_SESIONES_POR_DIA}"
            )
        for h in self.horas_recreo:
            if not (1 <= h <= self.sesiones_por_dia):
                raise ValueError(
                    f"hora_recreo={h} debe estar entre 1 y {self.sesiones_por_dia}"
                )

    def get_dias_nivel(self, nivel: str) -> list[str]:
        return self.dias_disponibles_por_nivel.get(nivel, DIAS_VALIDOS)

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
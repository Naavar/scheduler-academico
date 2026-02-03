from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class Hueco:
    dia: str
    hora_inicio: str
    hora_fin: str
    profesores_disponibles: List[str]

    @property
    def num_profesores(self) -> int:
        return len(self.profesores_disponibles)


class BuscadorHuecos:
    slot_minutos = 5
    hora_inicio = 7
    hora_fin = 22
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    def __init__(self, profesores_json: Dict[str, Any]):
        self.profesores_json = profesores_json
        sel
        

    def buscar_huecos(self, duracion: int = 60) -> Optional[Dict[str, Any]]:
        huecos = self.buscar_huecos_por_profesor(duracion=duracion)
        if not huecos:
            return None
        
        mejor = huecos[0]

        return {
            "dia": mejor.dia,
            "hora_inicio": mejor.hora_inicio,
            "hora_fin": mejor.hora_fin,
            "profesores_disponibles": mejor.profesores_disponibles,
            "num_profesores": mejor.num_profesores,
        }

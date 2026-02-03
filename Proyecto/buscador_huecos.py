from dataclasses import dataclass


@dataclass
class Hueco:
    dia: str
    hora_inicio: str
    hora_fin: str
    profesores_disponibles: list

    @property
    def num_profesores(self):
        return len(self.profesores_disponibles)


class BuscadorHuecos:
    slot_minutos = 5
    hora_inicio = 7
    hora_fin = 22
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    def __init__(self, profesores_json):
        self.profesores_json = profesores_json
        self.num_slots = ((self.hora_fin - self.hora_inicio) * 60) // self.slot_minutos
        self.disponibilidad = self.construir_disponibilidad()

    def hora_a_min(self, h):
        hh, mm = map(int, h.split(":"))
        return hh * 60 + mm

    def min_a_hora(self, m):
        hh = m // 60
        mm = m % 60
        return f"{hh:02d}:{mm:02d}"

    def construir_disponibilidad(self):
        disponibilidad = {}

        for dia in self.dias:
            disponibilidad[dia] = []

        inicio_dia = self.hora_inicio * 60
        fin_dia = self.hora_fin * 60

        for profe in self.profesores_json:
            libre_por_dia ={}
            for dia in self.dias:
                libre_por_dia[dia] = [True] * self.num_slots
            
            for eventos in profe.get("eventos", []):
                dia = eventos["dia"]
                if dia not in libre_por_dia:
                    continue
            
                inicio_evento = max(self.hora_a_min(eventos["inicio"]), inicio_dia)
                fin_evento = min(self.hora_a_min(eventos["fin"]), fin_dia)
                if fin_evento <= inicio_evento:
                    continue
                
                slot_inicio = (inicio_evento - inicio_dia) // self.slot_minutos
                slot_fin = (fin_evento - inicio_dia + self.slot_minutos - 1) // self.slot_minutos

                for slot in range(slot_inicio, min(slot_fin, self.num_slots)):
                    libre_por_dia[dia][slot] = False

            for dia in self.dias:
                disponibilidad[dia].append(libre_por_dia[dia])
        
        return disponibilidad


    def buscar_huecos_por_profesor(self, duracion=60):
        huecos = []
        slots_necesarios = duracion // self.slot_minutos
        inicio_dia = self.hora_inicio * 60

        



        return huecos

    def buscar_huecos(self, duracion=60):
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

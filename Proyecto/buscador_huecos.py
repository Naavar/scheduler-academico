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

def clave_num_profesores(hueco):
    return hueco.num_profesores

class BuscadorHuecos:
    slot_minutos = 5
    hora_inicio = 7
    hora_fin = 22
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    def __init__(self, profesores_json):
        self.profesores_json = profesores_json
        self.num_slots = ((self.hora_fin - self.hora_inicio) * 60) // self.slot_minutos
        self.horas = self._precalcular_horas()
        self.disponibilidad = self.construir_disponibilidad()

    def _precalcular_horas(self):
        horas = []
        minutos = self.hora_inicio * 60
        for slot in range(self.num_slots + 1):
            horas.append(self.min_a_hora(minutos))
            minutos += self.slot_minutos
        return horas


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


    def buscar_huecos_por_profesor(
        self,
        duracion=60,
        filtro_dia=None,
        turno=None,
        hora_min=None,
        hora_max=None):

        huecos = []
        slots_necesarios = duracion // self.slot_minutos
        inicio_dia = self.hora_inicio * 60

        min_slot = 0
        max_slot = self.num_slots

        if turno == "mañana":
            limite = self.hora_a_min("14:15")
            max_slot = (limite - inicio_dia) // self.slot_minutos
        elif turno == "tarde":
            limite = self.hora_a_min("14:15")
            min_slot = (limite - inicio_dia) // self.slot_minutos 

        if hora_min is not None:
            min_slot = max(min_slot, (self.hora_a_min(hora_min) - inicio_dia) // self.slot_minutos)

        if hora_max is not None:
            max_slot = min(max_slot, (self.hora_a_min(hora_max) - inicio_dia) // self.slot_minutos)

        end_slot = max_slot - slots_necesarios + 1

        for dia in self.dias:
            if filtro_dia and dia != filtro_dia:
                continue

            dia_libre = self.disponibilidad[dia]
            
            if not dia_libre:
                continue

            for slot_inicial in range(min_slot, end_slot):
                slot_final = slot_inicial + slots_necesarios
                
                profesores_candidatos = 0

                for profesor in range(len(self.profesores_json)):
                    if dia_libre[profesor][slot_inicial]:
                        profesores_candidatos += 1
                
                if profesores_candidatos < 3:
                    continue
                
                profesores_disponibles = []
                for profesor in range(len(self.profesores_json)):
                    if dia_libre[profesor][slot_inicial]:
                        if all(dia_libre[profesor][slot] for slot in range(slot_inicial, slot_final)):
                            profesores_disponibles.append(self.profesores_json[profesor]["profesor"]["nombre"])


                if profesores_disponibles:
                    hora_inicio = self.horas[slot_inicial]
                    hora_fin = self.horas[slot_final]

                    hueco = Hueco(dia = dia, hora_inicio = hora_inicio, hora_fin = hora_fin, profesores_disponibles = profesores_disponibles)
                    huecos.append(hueco)

        huecos.sort(key=clave_num_profesores, reverse=True)

        return huecos

    def buscar_huecos_n(self, duracion = 60, n=5):
        huecos = self.buscar_huecos_por_profesor(duracion=duracion)
        return huecos[:n]


    def buscar_hueco_comun(self, duracion=60):
        huecos = self.buscar_huecos_n(duracion=duracion, n=1)
        if not huecos:
            return None

        mejor_hueco = huecos[0]

        return {
            "dia": mejor_hueco.dia,
            "hora_inicio": mejor_hueco.hora_inicio,
            "hora_fin": mejor_hueco.hora_fin,
            "profesores_disponibles": mejor_hueco.profesores_disponibles,
            "num_profesores": mejor_hueco.num_profesores,
        }

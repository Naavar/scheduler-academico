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


def clave_num_profesores(hueco: Hueco) -> int:
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

    def hora_a_min(self, h: str) -> int:
        hh, mm = map(int, h.split(":"))
        return hh * 60 + mm

    def min_a_hora(self, m: int) -> str:
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
            libre_por_dia = {}
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

    def _backtracking_intervalo(
        self,
        dia_libre_dia,
        slot_inicial: int,
        slot_final: int,
        prof_idx: int,
        seleccion_actual: list,
        mejor: dict,
    ):
        num_profesores = len(dia_libre_dia)

        if prof_idx == num_profesores:
            if len(seleccion_actual) > mejor["num_profesores"]:
                mejor["num_profesores"] = len(seleccion_actual)
                mejor["profesores"] = seleccion_actual.copy()
            return

        restantes = num_profesores - prof_idx
        if len(seleccion_actual) + restantes <= mejor["num_profesores"]:
            return

        slots_profesor = dia_libre_dia[prof_idx]
        libre_todo = True
        for slot in range(slot_inicial, slot_final):
            if not slots_profesor[slot]:
                libre_todo = False
                break

        if libre_todo:
            seleccion_actual.append(prof_idx)
            self._backtracking_intervalo(
                dia_libre_dia,
                slot_inicial,
                slot_final,
                prof_idx + 1,
                seleccion_actual,
                mejor,
            )
            seleccion_actual.pop()

        self._backtracking_intervalo(
            dia_libre_dia,
            slot_inicial,
            slot_final,
            prof_idx + 1,
            seleccion_actual,
            mejor,
        )

    def buscar_huecos_por_profesor(
        self,
        duracion: int = 60,
        filtro_dia: str = None,
        turno: str = None,
        hora_min: str = None,
        hora_max: str = None,
    ):
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

            num_profesores = len(self.profesores_json)

            for slot_inicial in range(min_slot, end_slot):
                slot_final = slot_inicial + slots_necesarios

                profesores_candidatos = 0
                for profesor in range(num_profesores):
                    if dia_libre[profesor][slot_inicial]:
                        profesores_candidatos += 1

                if profesores_candidatos < 3:
                    continue

                mejor = {"num_profesores": 0, "profesores": []}
                self._backtracking_intervalo(
                    dia_libre,
                    slot_inicial,
                    slot_final,
                    prof_idx=0,
                    seleccion_actual=[],
                    mejor=mejor,
                )

                if mejor["num_profesores"] >= 3:
                    hora_inicio = self.horas[slot_inicial]
                    hora_fin = self.horas[slot_final]
                    profesores_disponibles = [
                        self.profesores_json[i]["profesor"]["nombre"]
                        for i in mejor["profesores"]
                    ]
                    hueco = Hueco(
                        dia=dia,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        profesores_disponibles=profesores_disponibles,
                    )
                    huecos.append(hueco)

        huecos.sort(key=clave_num_profesores, reverse=True)
        return huecos

    def buscar_huecos_n(self, duracion: int = 60, n: int = 5):
        huecos = self.buscar_huecos_por_profesor(duracion=duracion)
        return huecos[:n]

    def buscar_hueco_comun(self, duracion: int = 60):
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

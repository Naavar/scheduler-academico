import cProfile
import json

from buscador_huecos import BuscadorHuecos

profesores = []

for profesor in range(50):
    eventos = [{"dia": "Lunes", "inicio": "09:00", "fin": "10:00"}]
    profesores.append({"profesor": {"nombre": f"Prof{profesor}"}, "eventos": eventos})

pr = cProfile.Profile()
pr.enable()

buscador = BuscadorHuecos(profesores)
buscador.buscar_huecos_n(duracion=60)

pr.disable()
pr.print_stats(sort="time")
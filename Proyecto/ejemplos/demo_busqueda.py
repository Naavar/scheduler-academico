"""
Demo completo del sistema de búsqueda de huecos.
Muestra diferentes escenarios de uso del BuscadorHuecos.
"""

import json
from pathlib import Path
from buscador_huecos import BuscadorHuecos


def cargar_datos_ejemplo():
    """Carga datos de ejemplo (puedes usar archivos JSON reales o crear aquí)."""
    profesores = [
        {
            "profesor": {"nombre": "Dr. García", "codigo": "P001"},
            "eventos": [
                {"dia": "Lunes", "inicio": "09:00", "fin": "11:00"},
                {"dia": "Martes", "inicio": "10:00", "fin": "12:00"},
            ]
        },
        {
            "profesor": {"nombre": "Dra. López", "codigo": "P002"},
            "eventos": [
                {"dia": "Lunes", "inicio": "14:00", "fin": "16:00"},
                {"dia": "Miércoles", "inicio": "09:00", "fin": "11:00"},
            ]
        },
        {
            "profesor": {"nombre": "Dr. Martínez", "codigo": "P003"},
            "eventos": [
                {"dia": "Lunes", "inicio": "11:00", "fin": "13:00"},
                {"dia": "Jueves", "inicio": "15:00", "fin": "17:00"},
            ]
        },
    ]
    return profesores


def ejemplo_1_busqueda_simple():
    """Escenario 1: Búsqueda simple sin filtros."""
    print("=" * 60)
    print("EJEMPLO 1: Búsqueda simple de hueco común")
    print("=" * 60)
    
    profesores = cargar_datos_ejemplo()
    buscador = BuscadorHuecos(profesores)
    
    # Buscar mejor hueco de 60 minutos
    resultado = buscador.buscar_hueco_comun(duracion=60)
    
    if resultado:
        print(f" Hueco encontrado:")
        print(f"  Día: {resultado['dia']}")
        print(f"  Horario: {resultado['hora_inicio']} - {resultado['hora_fin']}")
        print(f"  Profesores disponibles ({resultado['num_profesores']}):")
        for prof in resultado['profesores_disponibles']:
            print(f"    - {prof}")
    else:
        print("✗ No se encontraron huecos comunes")
    print()


def ejemplo_2_top_n_huecos():
    """Escenario 2: Obtener los 5 mejores huecos."""
    print("=" * 60)
    print("EJEMPLO 2: Top 5 mejores huecos")
    print("=" * 60)
    
    profesores = cargar_datos_ejemplo()
    buscador = BuscadorHuecos(profesores)
    
    huecos = buscador.buscar_huecos_n(duracion=60, n=5)
    
    print(f"Se encontraron {len(huecos)} huecos:")
    for i, hueco in enumerate(huecos, 1):
        print(f"\n{i}. {hueco.dia} {hueco.hora_inicio}-{hueco.hora_fin}")
        print(f"   Profesores ({hueco.num_profesores}): {', '.join(hueco.profesores_disponibles)}")
    print()


def ejemplo_3_filtro_dia():
    """Escenario 3: Buscar solo en un día específico."""
    print("=" * 60)
    print("EJEMPLO 3: Búsqueda filtrada por día (solo Lunes)")
    print("=" * 60)
    
    profesores = cargar_datos_ejemplo()
    buscador = BuscadorHuecos(profesores)
    
    huecos = buscador.buscar_huecos_por_profesor(
        duracion=60,
        filtro_dia="Lunes"
    )
    
    print(f"Huecos encontrados el Lunes: {len(huecos)}")
    for hueco in huecos[:3]:  # Mostrar primeros 3
        print(f"  • {hueco.hora_inicio}-{hueco.hora_fin}: {hueco.num_profesores} profesores")
    print()


def ejemplo_4_filtro_turno():
    """Escenario 4: Buscar solo en turno de mañana."""
    print("=" * 60)
    print("EJEMPLO 4: Búsqueda en turno de mañana")
    print("=" * 60)
    
    profesores = cargar_datos_ejemplo()
    buscador = BuscadorHuecos(profesores)
    
    huecos = buscador.buscar_huecos_por_profesor(
        duracion=60,
        turno="mañana"
    )
    
    print(f"Huecos en turno mañana: {len(huecos)}")
    for hueco in huecos[:3]:
        print(f"  • {hueco.dia} {hueco.hora_inicio}-{hueco.hora_fin}")
    print()


def ejemplo_5_filtro_rango_horario():
    """Escenario 5: Buscar en rango horario específico."""
    print("=" * 60)
    print("EJEMPLO 5: Búsqueda en rango 10:00-13:00")
    print("=" * 60)
    
    profesores = cargar_datos_ejemplo()
    buscador = BuscadorHuecos(profesores)
    
    huecos = buscador.buscar_huecos_por_profesor(
        duracion=60,
        hora_min="10:00",
        hora_max="13:00"
    )
    
    print(f"Huecos en rango 10:00-13:00: {len(huecos)}")
    for hueco in huecos:
        print(f"  • {hueco.dia} {hueco.hora_inicio}-{hueco.hora_fin}: {hueco.num_profesores} prof.")
    print()


def ejemplo_6_sin_resultados():
    """Escenario 6: Caso donde no hay huecos comunes."""
    print("=" * 60)
    print("EJEMPLO 6: Escenario sin huecos disponibles")
    print("=" * 60)
    
    # Profesores completamente ocupados
    profesores = [
        {
            "profesor": {"nombre": "Prof1"},
            "eventos": [
                {"dia": "Lunes", "inicio": "07:00", "fin": "22:00"},
                {"dia": "Martes", "inicio": "07:00", "fin": "22:00"},
                {"dia": "Miércoles", "inicio": "07:00", "fin": "22:00"},
                {"dia": "Jueves", "inicio": "07:00", "fin": "22:00"},
                {"dia": "Viernes", "inicio": "07:00", "fin": "22:00"},
            ]
        },
        {
            "profesor": {"nombre": "Prof2"},
            "eventos": [
                {"dia": "Lunes", "inicio": "07:00", "fin": "22:00"},
                {"dia": "Martes", "inicio": "07:00", "fin": "22:00"},
                {"dia": "Miércoles", "inicio": "07:00", "fin": "22:00"},
                {"dia": "Jueves", "inicio": "07:00", "fin": "22:00"},
                {"dia": "Viernes", "inicio": "07:00", "fin": "22:00"},
            ]
        },
        {
            "profesor": {"nombre": "Prof3"},
            "eventos": [
                {"dia": "Lunes", "inicio": "07:00", "fin": "22:00"},
                {"dia": "Martes", "inicio": "07:00", "fin": "22:00"},
                {"dia": "Miércoles", "inicio": "07:00", "fin": "22:00"},
                {"dia": "Jueves", "inicio": "07:00", "fin": "22:00"},
                {"dia": "Viernes", "inicio": "07:00", "fin": "22:00"},
            ]
        },
    ]

    
    buscador = BuscadorHuecos(profesores)
    resultado = buscador.buscar_hueco_comun(duracion=60)
    
    if resultado:
        print(f" Hueco encontrado: {resultado['dia']} {resultado['hora_inicio']}")
    else:
        print(" No se encontraron huecos comunes (esperado)")
    print()


def ejemplo_7_combinacion_filtros():
    """Escenario 7: Combinar múltiples filtros."""
    print("=" * 60)
    print("EJEMPLO 7: Filtros combinados (Martes, tarde, 15:00-18:00)")
    print("=" * 60)
    
    profesores = cargar_datos_ejemplo()
    buscador = BuscadorHuecos(profesores)
    
    huecos = buscador.buscar_huecos_por_profesor(
        duracion=60,
        filtro_dia="Martes",
        turno="tarde",
        hora_min="15:00",
        hora_max="18:00"
    )
    
    print(f"Huecos con filtros combinados: {len(huecos)}")
    for hueco in huecos:
        print(f"  • {hueco.hora_inicio}-{hueco.hora_fin}: {', '.join(hueco.profesores_disponibles)}")
    print()


if __name__ == "__main__":
    
    ejemplo_1_busqueda_simple()
    ejemplo_2_top_n_huecos()
    ejemplo_3_filtro_dia()
    ejemplo_4_filtro_turno()
    ejemplo_5_filtro_rango_horario()
    ejemplo_6_sin_resultados()
    ejemplo_7_combinacion_filtros()
    
    print("=" * 60)
    print("Demo completada")
    print("=" * 60)

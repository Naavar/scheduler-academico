import sys
sys.path.insert(0, './Proyecto')
from app import cargar_datos_desde_json, build_config_from_params, GRUPOS_POR_CODIGO
from buscador_evaluacion import buscar_sesion_evaluacion

niveles, g_por_nivel, g_por_codigo = cargar_datos_desde_json('data/horarios_consolidados.json')
import json
profesores = json.load(open('data/horarios_consolidados.json', encoding='utf-8'))
config = build_config_from_params('BACHILLERATO', ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'], 4, False, False, False)

bachilleratos = ['B1ACI', 'B2AC', 'B1BSO', 'B2BSO']
print(f'Bachilleratos a procesar: {bachilleratos}')

codigos_por_nombre = { p['profesor'].get('nombre', p['profesor'].get('codigo', 'SIN')): p['profesor']['codigo'] for p in profesores }

def profesores_de_curso(curso_sel, nivel_sel):
    nombres, codigos = {}, {}
    for p in profesores:
        codigo = p['profesor']['codigo']
        cursos_prof = set(GRUPOS_POR_CODIGO.get(codigo, {}).get(nivel_sel, []))
        if curso_sel in cursos_prof:
            nombre = p['profesor'].get('nombre', codigo)
            nombres[nombre] = codigo
    return nombres

resultados = {}
for curso in bachilleratos:
    nombres = profesores_de_curso(curso, 'BACHILLERATO')
    eq = set(nombres.values())
    
    slots_a_bloquear = []
    
    for curso_prev, res_prev in resultados.items():
        if res_prev.sin_solucion: continue
        codigos_prev = {d.codigo for d in res_prev.detalle}
        shared = codigos_prev.intersection(eq)
        if shared:
            print(f'  Compartidos con {curso_prev}: {len(shared)}')
            eq -= shared
            slots_a_bloquear.append((res_prev.dia, res_prev.hora_inicio))
    
    print(f'Procesando {curso} con {len(eq)} profesores y slots a bloquear: {slots_a_bloquear}')
    res = buscar_sesion_evaluacion(
        profesores, eq, config=config, 
        dias_disponibles=['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'], duracion_minutos=55, 
        resultados_previos=resultados, slots_a_bloquear=slots_a_bloquear
    )
    resultados[curso] = res
    if res.sin_solucion:
        print(f'  -> SIN SOLUCION: {res.explicacion}')
        print(f'  -> Bloqueadores: {res.diagnostico_bloqueadores[:3]}')
    else:
        print(f'  -> SOLUCION: {res.dia} {res.hora_inicio} a {res.hora_fin}')


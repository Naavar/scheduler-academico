import sys
sys.path.insert(0, './Proyecto')
from app import cargar_datos_desde_json, build_config_from_params, GRUPOS_POR_CODIGO
from buscador_evaluacion import buscar_sesion_evaluacion, hora_a_minutos
import json

niveles, g_por_nivel, g_por_codigo = cargar_datos_desde_json('data/horarios_consolidados.json')
profesores = json.load(open('data/horarios_consolidados.json', encoding='utf-8'))
config = build_config_from_params('BACHILLERATO', ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'], 4, False, False, False)

bachilleratos = ['B1ACI', 'B2AC', 'B1BSO', 'B2BSO']
codigos_por_nombre = { p['profesor'].get('nombre', p['profesor'].get('codigo', 'SIN')): p['profesor']['codigo'] for p in profesores }
profesores_dict = {p['profesor']['codigo']: p for p in profesores}

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
    
    res = buscar_sesion_evaluacion(
        profesores, eq, config=config, 
        dias_disponibles=['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'], duracion_minutos=55, 
        resultados_previos=resultados
    )
    resultados[curso] = res
    if not res.sin_solucion:
        print(f"\n======== VERIFICANDO {curso} ========")
        print(f"Asignado: {res.dia} de {res.hora_inicio} a {res.hora_fin}")
        
        m_ini = hora_a_minutos(res.hora_inicio)
        m_fin = hora_a_minutos(res.hora_fin)
        
        conflictos = 0
        for cod in eq:
            prof = profesores_dict[cod]
            nombre = prof["profesor"].get("nombre", cod)
            
            # Buscar si el profe tiene clase a esa hora
            for evento in prof.get("eventos", []):
                if evento.get("dia") == res.dia:
                    e_ini = hora_a_minutos(evento["inicio"].strip())
                    e_fin = hora_a_minutos(evento["fin"].strip())
                    
                    # Chequear solapamiento
                    if e_ini < m_fin and e_fin > m_ini:
                        print(f"  [CONFLICTO] {nombre} tiene {evento['actividad']} con {evento['grupos']} de {evento['inicio']} a {evento['fin']}")
                        conflictos += 1
                        
        if conflictos == 0:
            print("  [EXITO] 0 CONFLICTOS. Todos los profesores estan libres.")

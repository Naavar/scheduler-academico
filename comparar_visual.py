#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comparador Visual: PDF vs JSON lado a lado"""

import json
import pdfplumber
import sys
import io
from pathlib import Path
from pdf2image import convert_from_path
import base64
from io import BytesIO

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def generar_html_comparacion(pdf_path, json_path, output_path, paginas_a_revisar=None):
    """Genera HTML con comparación visual PDF vs JSON"""
    
    # Cargar JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data_json = json.load(f)
    
    # Convertir PDF a imágenes
    print("Convirtiendo PDF a imagenes...")
    images = convert_from_path(pdf_path, dpi=150)
    
    # Si no se especifican páginas, mostrar todas
    if paginas_a_revisar is None:
        paginas_a_revisar = range(min(len(images), len(data_json)))
    
    # Generar HTML
    html = """
<!DOCTYPE html>     
<html>
<head>
    <meta charset="UTF-8">
    <title>Comparación PDF vs JSON</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .comparacion { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
            margin-bottom: 40px;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .panel { border: 2px solid #ddd; padding: 15px; border-radius: 5px; }
        .panel h3 { margin-top: 0; color: #333; }
        .pdf-image { max-width: 100%; border: 1px solid #ccc; }
        .evento { 
            padding: 8px; 
            margin: 5px 0; 
            background: #f0f8ff; 
            border-left: 4px solid #4CAF50;
            border-radius: 3px;
        }
        .evento-largo { border-left-color: #FF9800; background: #fff3e0; }
        .dia { font-weight: bold; color: #2196F3; }
        .hora { color: #666; font-size: 0.9em; }
        .asignatura { margin-top: 3px; }
        .duracion { 
            display: inline-block; 
            background: #FF9800; 
            color: white; 
            padding: 2px 6px; 
            border-radius: 3px; 
            font-size: 0.8em;
            margin-left: 5px;
        }
        .info-profesor { 
            background: #e3f2fd; 
            padding: 10px; 
            border-radius: 5px; 
            margin-bottom: 15px;
        }
        .navegacion {
            position: sticky;
            top: 0;
            background: white;
            padding: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            border-radius: 5px;
            z-index: 1000;
            max-height: 120px;
            overflow-y: auto;
        }
        .btn { 
            padding: 8px 15px; 
            margin: 0 5px; 
            background: #2196F3; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { background: #1976D2; }
        .alerta { background: #fff3cd; border-left-color: #ff5722; }
    </style>
</head>
<body>
    <h1>Comparacion Visual: PDF vs JSON</h1>
    <div class="navegacion">
        <strong>Navegacion:</strong>
"""
    
    # Índice de navegación
    for i in paginas_a_revisar:
        if i < len(data_json):
            nombre = data_json[i]['profesor']['nombre']
            html += f'<a href="#pagina-{i+1}" class="btn">Pag {i+1}</a>\n'
    
    html += "</div>\n"
    
    # Generar comparaciones
    for idx in paginas_a_revisar:
        if idx >= len(images) or idx >= len(data_json):
            continue
        
        print(f"Procesando pagina {idx+1}...")
        
        # Convertir imagen a base64
        buffered = BytesIO()
        images[idx].save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Datos JSON
        horario = data_json[idx]
        profesor = horario['profesor']
        eventos = horario['eventos']
        
        # Calcular duración de cada evento
        eventos_con_duracion = []
        for evento in eventos:
            try:
                h_inicio = evento['inicio'].split(':')
                h_fin = evento['fin'].split(':')
                minutos_inicio = int(h_inicio[0]) * 60 + int(h_inicio[1])
                minutos_fin = int(h_fin[0]) * 60 + int(h_fin[1])
                duracion = minutos_fin - minutos_inicio
                eventos_con_duracion.append((evento, duracion))
            except:
                eventos_con_duracion.append((evento, 0))
        
        # Agrupar por día
        eventos_por_dia = {}
        for evento, duracion in eventos_con_duracion:
            dia = evento['dia']
            if dia not in eventos_por_dia:
                eventos_por_dia[dia] = []
            eventos_por_dia[dia].append((evento, duracion))
        
        html += f"""
    <div id="pagina-{idx+1}" class="comparacion">
        <div class="panel">
            <h3>PDF - Pagina {idx+1}</h3>
            <img src="data:image/png;base64,{img_str}" class="pdf-image" alt="Pagina {idx+1}">
        </div>
        
        <div class="panel">
            <h3>JSON Extraido</h3>
            <div class="info-profesor">
                <strong>Profesor:</strong> {profesor['nombre']}<br>
                <strong>Codigo:</strong> {profesor['codigo']}<br>
                <strong>Total eventos:</strong> {len(eventos)}
            </div>
"""
        
        # Mostrar eventos por día
        for dia in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']:
            if dia in eventos_por_dia:
                html += f'<div class="dia">{dia}</div>\n'
                for evento, duracion in eventos_por_dia[dia]:
                    # Marcar eventos largos (>60 min = posible rowspan)
                    clase_extra = "evento-largo" if duracion > 60 else ""
                    alerta = "alerta" if duracion > 180 else ""
                    
                    duracion_html = ""
                    if duracion > 60:
                        horas = duracion // 60
                        mins = duracion % 60
                        duracion_html = f'<span class="duracion">{horas}h {mins}min</span>'
                    
                    html += f"""
                <div class="evento {clase_extra} {alerta}">
                    <div class="hora">{evento['inicio']} - {evento['fin']} {duracion_html}</div>
                    <div class="asignatura">{evento['asignatura']}</div>
                </div>
"""
        
        html += """
        </div>
    </div>
"""
    
    html += """
</body>
</html>
"""
    
    # Guardar HTML
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\nComparacion generada: {output_path}")
    print(f"Total paginas comparadas: {len(paginas_a_revisar)}")

def main():
    base_path = Path(__file__).parent
    pdf_path = base_path / "data" / "HORARIOS_25_26 - Docentes_anon.pdf"
    json_path = base_path / "data" / "horarios_consolidados.json"
    output_path = base_path / "comparacion_visual.html"
    
    if not pdf_path.exists():
        print(f"Error: No se encontro {pdf_path}")
        return 1
    
    if not json_path.exists():
        print(f"Error: No se encontro {json_path}")
        return 1
    
    print("Generando comparacion visual PDF vs JSON...")
    print("Esto puede tardar 1-2 minutos para 134 paginas...")
    
    # Opción: Generar solo primeras 20 páginas para prueba rápida
    # paginas = range(20)  # Descomentar para prueba rápida
    paginas = None  # Todas las páginas
    
    try:
        generar_html_comparacion(pdf_path, json_path, output_path, paginas)
        print(f"\nAbre el archivo en tu navegador: {output_path}")
        print("\nLeyenda:")
        print("   - Eventos normales (verde): <=60 minutos")
        print("   - Eventos largos (naranja): >60 minutos (posible rowspan)")
        print("   - Eventos muy largos (rojo): >180 minutos (verificar)")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nInstala las dependencias necesarias:")
        print("   pip install pdf2image pillow")
        print("   En Windows tambien necesitas: poppler")
        print("   Descarga: https://github.com/oschwartz10612/poppler-windows/releases/")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

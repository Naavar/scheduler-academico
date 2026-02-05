📅 Sistema de Extracción y Consolidación de Horarios

> **Backend de Extracción:** Módulo encargado de leer archivos PDF académicos, extraer información mediante lógica posicional y semántica, 
> validarla y generar un JSON maestro para el algoritmo de búsqueda de huecos.

| 👤 Responsable | 🛠️ Rol | ✅ Estado |
| **Lucas** | Backend & Integración | **Sprints 1-3 Completados** |

## 🚀 Funcionalidades Principales

### 1. 📥 Extracción Inteligente (PDF a Datos)
* **Motor Potente:** Utiliza `pdfplumber` para analizar archivos vectoriales con precisión.
* **Auto-Detección:** Reconoce automáticamente la estructura de la tabla (columnas de días `L-V` y filas de horas).
* **Identificación Contextual:** Clasifica asignaturas basándose en posición, color de fondo hexadecimal y similitud de texto.
* **Agrupación Lógica:** Fusiona bloques contiguos que pertenecen a la misma clase.

### 2. 🧹 Limpieza y Normalización
* **Filtro de Ruido:** Elimina automáticamente filas de "Recreo", celdas vacías o metadatos irrelevantes.
* **Estandarización:** Convierte cualquier formato de hora al estándar ISO `HH:MM`.
* **Corrección Automática:** * *Problema:* PDF indica `18:35 - 18:35`.
    * *Solución:* El sistema detecta la igualdad y suma 55 minutos automáticamente -> `18:35 - 19:30`.

### 3. 🏭 Consolidación Masiva
* Escaneo recursivo de la carpeta `data/` buscando archivos `*.pdf`.
* Procesamiento en lote de todas las páginas.
* Generación de un único artefacto de salida: `horarios_consolidados.json`.

### 4. 🛡️ Control de Calidad (Validación)
Cada horario pasa por un control estricto (`validacion.py`) antes de ser aceptado:
* ✅ Verifica existencia de Nombre y Código de profesor.
* ✅ Valida que los días sean `Lunes` a `Viernes`.
* ✅ Comprueba la lógica temporal (`Hora Fin` > `Hora Inicio`).
* ❌ **Rechazo:** Si un horario es defectuoso, se descarta y notifica sin detener el pipeline.


## 🛠️ Estructura del Módulo

```text
Proyecto/
├── consolidador.py   # 🧠 ORQUESTADOR: Script principal. Lee PDFs y coordina.
├── validacion.py     # 🛡️ QA: Verifica que los datos cumplan el contrato.
└── utils.py          # 🔧 UTILS: Funciones auxiliares (fechas, texto, colores).
data/
├── horarios_consolidados.json  # 📤 SALIDA: Resultado final (Artifact).
└── *.pdf                       # 📥 ENTRADA: Archivos crudos.
📋 Requisitos PreviosAsegúrate de instalar las dependencias necesarias en tu entorno virtual:Bashpip install pdfplumber jsonschema
▶️ Guía de Uso RápidaSigue estos pasos para procesar nuevos horarios:Prepara los datos:Coloca todos tus archivos PDF (sin importar el nombre) en la carpeta data/.Ejecuta el consolidador:Desde la terminal, navega a la carpeta Proyecto y ejecuta:Bashpython consolidador.py
Verifica el resultado:Observarás el progreso en la consola. Al finalizar, se generará o sobreescribirá el archivo data/horarios_consolidados.json.📦 Formato de Salida (JSON)El archivo generado sigue el Contrato de Interfaz V1 para integración con el algoritmo de backtracking:JSON[
  {
    "profesor": {
      "nombre": "GARCIA LOPEZ, ANA",
      "codigo": "mat.mat.AGL123"
    },
    "eventos": [
      {
        "dia": "Lunes",
        "asignatura": "MATEMÁTICAS II",
        "inicio": "09:00",
        "fin": "10:50"
      },
      {
        "dia": "Martes",
        "asignatura": "TUTORÍA",
        "inicio": "11:30",
        "fin": "12:25"
      }
    ]
  }
]
⚠️ Manejo de Errores
El sistema está diseñado para ser resiliente (Fail-Safe):
Error Potencial: Comportamiento del Sistema
PDF Corrupto: Se omite el archivo, se registra el error y continúa con el siguiente.
Página Vacía: Se ignora y pasa a la siguiente página.
Datos Inválidos: Si una hora es incoherente (ej: 25:00), solo se descarta esa página específica.
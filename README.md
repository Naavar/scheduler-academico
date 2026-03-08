# Extractor de Horarios desde PDF (Determinista)

Este proyecto implementa un **extractor automático de horarios escolares en formato PDF**
utilizando **análisis estructural del documento** (coordenadas, rejillas y celdas),
sin depender de servicios externos ni APIs de IA.

El objetivo es generar un **JSON limpio y normalizado** a partir de horarios reales,
para poder aplicar posteriormente algoritmos de **búsqueda de huecos, intersección de agendas
y planificación automática de reuniones**.

---
# Interfaz Web (Streamlit): ejecución y guía de uso

Además del extractor determinista (Proyecto/main.py), el proyecto incluye una interfaz gráfica desarrollada con Streamlit para:
* Cargar uno o varios PDFs de horarios.
* Extraer/normalizar los eventos.
* Calcular huecos comunes entre profesores.
* Filtrar resultados por duración, día y turno.
* Exportar los resultados a Excel (.xlsx).

## Ejecutar la aplicación (Streamlit)

Desde la raíz del repositorio, ejecuta:

```bash
streamlit run Proyecto/app.py
```
Streamlit abrirá la interfaz en tu navegador (normalmente en http://localhost:8501).

## Cómo funciona la interfaz

La interfaz está organizada en **3 bloques principales**:

---

### 1) Cargar horarios en PDF

En la parte superior verás el apartado **“Cargar horarios en PDF”**:

- Puedes **arrastrar y soltar** archivos PDF o pulsar **“Browse files”**.
- Se permiten **uno o varios PDFs** (por ejemplo, horarios de distintos profesores).
- Tras seleccionar los PDFs, pulsa el botón **“Cargar horarios desde PDF”**.

#### Qué hace internamente

- Lee cada PDF (texto seleccionable).
- Detecta rejilla y celdas mediante coordenadas (X/Y).
- Genera los eventos normalizados por profesor.
- Prepara una estructura común para poder cruzar disponibilidades.

---

### 2) Parámetros de búsqueda (filtros)

En el apartado **“Parámetros de búsqueda”** puedes ajustar los filtros antes de buscar huecos.

#### Duración de la reunión (minutos)

- Control tipo *slider* (por ejemplo, **30 minutos**).
- Determina el tamaño mínimo de cada hueco encontrado.
- Ejemplo:
  - Si eliges **60 min**, solo se mostrarán huecos de 1 hora o más.

#### Día

Desplegable con:

- **Todos** → muestra huecos en cualquier día.
- Día concreto → Lunes, Martes, etc. (según el horario detectado).

#### Turno

Selector con opciones:

- **Todos**
- **Mañana**
- **Tarde**

#### Resumen de filtros

A la derecha aparece un bloque **“Resumen de filtros”** que permite comprobar de un vistazo:

- Duración seleccionada
- Día
- Turno

---

### 3) Búsqueda de huecos comunes

En el bloque **“Búsqueda de huecos comunes”**:

- Pulsa **“Buscar huecos comunes”** para ejecutar el cálculo con los filtros actuales.
- La aplicación mostrará un mensaje informativo, por ejemplo:

  > *“Se han encontrado X huecos.”*

---

### Tabla: Mejores huecos

Los resultados aparecen en una tabla con columnas como:

- **Día**
- **Hora inicio**
- **Hora fin**
- **Profesores** (lista de profesores disponibles)
- **Prof. disponibles** (número total de profesores libres en esa franja)

#### Criterios de priorización

En general, se priorizan los huecos que:

- Cumplen la duración mínima configurada.
- Tienen más profesores disponibles.
- Encajan con el día y turno seleccionados.

---

## Exportar resultados a Excel (.xlsx)

En la sección de resultados hay un botón **“Exportar a Excel”**.

- Al pulsarlo, se descarga automáticamente un archivo **`.xlsx`**.
- El Excel incluye columnas como:
  - Día
  - Hora inicio
  - Hora fin
  - Profesores
  - Número de disponibles
- Permite compartir los resultados o analizarlos posteriormente.

> **Nota:** Si no se ha ejecutado la búsqueda o no hay resultados, el archivo exportado no contendrá datos relevantes.

---

## Enfoque Técnico

-  PDF con texto seleccionable
-  Análisis por coordenadas (X/Y)
-  Detección de:
   - días
   - franjas horarias
   - celdas continuas (clases de 2–3 horas)
-  Normalización y fusión de eventos
-  Salida JSON estructurada

 **No se usa IA en el extractor actual**: el proceso es **determinista, reproducible y offline**.

---

##  Estructura del Proyecto

Proyecto_Horarios/
│
├── Proyecto/
│ ├── extractor_pdf.py # Lógica principal de extracción PDF → JSON
│ ├── main.py # Punto de entrada y validación
│ └── generador_datos.py # (opcional) generación de datos sintéticos
│
├── samples/
│ └── horario_ejemplo.pdf
│
├── requirements.txt
├── README.md
└── .gitignore

---

## Requisitos

- Python **3.10+**
- PDF con texto seleccionable

---

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

---

## Uso
1. Coloca un PDF de horario en el proyecto
2. Ejecuta:
```bash
python Proyecto/main.py
```

---
## Salida
El programa genera por consola (o redirigible a archivo):
```json
{
  "profesor": {
    "nombre": "...",
    "codigo": "..."
  },
  "eventos": [
    {
      "dia": "Martes",
      "turno": "mañana",
      "inicio": "16:15",
      "fin": "18:05",
      "titulo": "DESARROLLO WEB EN ENTORNO SERVIDOR 2DAW~2DAWM, 2DAW~2DAWN C06"
    }
  ]
}
```

---

## Próximos Pasos
* Procesamiento en batch de múltiples PDFs
* Cálculo de disponibilidad por profesor
* Intersección de huecos comunes
* Algoritmo de planificación de reuniones (≥ 1 hora)

---

## Nota sobre IA (histórico)
En una fase inicial se experimentó con Google Gemini (visión + texto) para interpretar
la estructura del PDF.
Finalmente, se optó por un enfoque determinista por ser:
* Más estable
* Reproducible
* Offline
* Sin dependencias externas
* y GRATIS
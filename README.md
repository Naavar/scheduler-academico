# Extractor de Horarios desde PDF (Determinista)

Este proyecto implementa un **extractor automático de horarios escolares en formato PDF**
utilizando **análisis estructural del documento** (coordenadas, rejillas y celdas),
sin depender de servicios externos ni APIs de IA.

El objetivo es generar un **JSON limpio y normalizado** a partir de horarios reales,
para poder aplicar posteriormente algoritmos de **búsqueda de huecos, intersección de agendas
y planificación automática de reuniones**.

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
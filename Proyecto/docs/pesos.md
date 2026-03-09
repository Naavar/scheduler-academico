# PESOS.md — Sistema de Pesos para Evaluación de Slots

**Autor:** Sergio  
**Sprint:** 0 (diseño) → 1 (implementación final)

---

## 1. Objetivo

El sistema de pesos permite al algoritmo de backtracking comparar objetivamente
qué slot de evaluación perjudica menos al equipo de profesores. A mayor peso,
peor es ese slot para el profesor implicado.

---

## 2. Tabla de pesos definitiva

| Caso | Peso añadido | Justificación |
|---|---|---|
| Sin sesiones ese día | base = 8 | El profesor no tiene referencia horaria ese día |
| Distancia 0 (adyacente) | base = 0 | Mínima disrupción |
| Distancia N franjas | base = N | A mayor separación, mayor disrupción |
| Slot es 7ª hora (permitida) | +2 | Extensión de jornada, penalización moderada |
| Slot es recreo (permitido) | +3 | Tiempo de descanso, penalización alta |
| Slot es hora no obligatoria | +2 | Fuera de permanencia, penalización moderada |

Principio de monotonía: a mayor distancia, mayor peso, sin saltos irregulares.

---

## 3. Pseudocódigo

función calcular_peso(codigo, dia_idx, franja_idx, indices, config):

    franjas_dia ← índices de franjas ocupadas por `codigo` en `dia_idx`

    si franjas_dia está vacío:
        peso ← 8
    sino:
        pos ← bisect(franjas_dia, franja_idx)
        distancia ← mínimo(|franjas_dia[pos] - franja_idx|,
                           |franjas_dia[pos-1] - franja_idx|)
        peso ← distancia

    si franja_idx == 7ª_hora Y config.permitir_septima_hora:
        peso ← peso + 2

    si franja_idx == recreo Y config.permitir_recreo:
        peso ← peso + 3

    si hora ∈ horas_no_obligatorias(codigo) Y config.permitir_horas_no_obligatorias:
        peso ← peso + 2

    retornar peso

---

## 4. Casos de ejemplo

| Sesiones del profesor | Franja evaluada | Peso base | Extras | Total |
|---|---|---|---|---|
| [2, 5, 7] | 3 | 1 | — | 1 |
| [1, 7] | 4 | 3 | — | 3 |
| [] | cualquiera | 8 | — | 8 |
| [3, 6] | 7ª hora | 2 | +2 | 4 |
| [2, 4] | recreo | 1 | +3 | 4 |
| [1, 3] | no oblig. | 3 | +2 | 5 |
| [3] | 7ª + no oblig. | 5 | +4 | 9 |

---

## 5. Decisiones de diseño

- Por qué 8 para "sin sesiones": es el valor más alto posible (máximo 7 franjas
  en un día de 7 horas), así siempre es peor que cualquier slot adyacente real.
- Por qué +3 para recreo y no +2: es el único descanso garantizado del profesor,
  afecta a todos por igual → penalización mayor.
- Por qué la función es pura: sin efectos secundarios, solo lee indices y config.
  Facilita el testing, debugging y paralelización futura.
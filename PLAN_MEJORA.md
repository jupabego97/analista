# Plan de mejora — Analista de Negocio con IA

## 1) Contexto confirmado

Este plan se construye con tus respuestas:

- Usuario principal: **solo gerente**.
- Flujo principal: **chat libre** para responder cualquier pregunta de negocio.
- Preguntas críticas iniciales:
  - ¿Qué se vendió ayer?
  - ¿Qué le debo comprar a X proveedor?
  - ¿A qué proveedor le debo comprar y qué productos?
  - ¿Qué productos se agotaron en los últimos 7 días?
- Expectativa de calidad: **respuestas fiables**.
- Alcance de datos final: **`facturas`, `facturas_proveedor`, `items`** (actualizadas por ETL diario).
- Sin multiusuario, sin auditoría obligatoria, sin requisitos regulatorios adicionales por ahora.
- Modelo LLM: **Gemini obligatorio**.
- Plataforma objetivo: **Railway**.

---

## 2) Objetivo de arquitectura

Diseñar una solución **estable, confiable y mantenible** para un caso de uso de análisis gerencial, priorizando:

1. **Fiabilidad de respuesta** (menos alucinación y más trazabilidad).
2. **Bajo riesgo operativo** (consultas seguras y controladas).
3. **Mantenibilidad** (separación de responsabilidades y pruebas).
4. **Evolución rápida** (añadir nuevos análisis sin romper lo existente).

---

## 3) Diagnóstico de la base actual

- El proyecto está implementado mayormente en un archivo monolítico (`app_analista_negocio.py`).
- El flujo mezcla UI, lógica de negocio, acceso a datos, seguridad SQL y orquestación LLM en la misma capa.
- La validación SQL actual por palabras clave ayuda, pero no garantiza control fino de columnas/tablas ni costo de consulta.
- Falta una capa formal de métricas de calidad de respuesta y pruebas automatizadas.

Implicación: el MVP funciona, pero para “respuestas fiables” conviene pasar a una arquitectura por capas con guardrails más fuertes.

---

## 4) Arquitectura objetivo (v1)

## 4.1 Capas

```text
Streamlit UI
   │
   ▼
Application Service (orquestación de pregunta)
   │
   ├── Intent Router (clasifica intención: ventas, compras, inventario, proveedor)
   ├── SQL Builder/Policy (genera SQL con restricciones)
   ├── Query Executor (ejecuta SQL y controla límites)
   ├── Insight Generator (explicación gerencial en español)
   └── Viz Recommender (tipo de gráfico)
   │
   ▼
Data Access Layer
   ├── PostgreSQL (tablas + vistas de negocio)
   └── Catálogo de métricas/KPIs
```

## 4.2 Módulos propuestos

- `ui/streamlit_app.py`: interfaz y estado de sesión.
- `services/question_service.py`: flujo principal pregunta → respuesta.
- `services/intent_service.py`: clasificación de intención y plantillas.
- `services/sql_policy.py`: reglas de seguridad/allowlist SQL.
- `services/analysis_service.py`: resumen ejecutivo y recomendaciones.
- `data/repositories.py`: acceso SQL tipado/encapsulado.
- `data/views.sql`: vistas de negocio para consultas frecuentes.
- `core/config.py`: variables de entorno y validación de configuración.
- `core/schemas.py`: contratos de I/O (pydantic/dataclasses).

---

## 5) Estrategia de fiabilidad (prioridad máxima)

## 5.1 Patrón recomendado: “SQL-first, explicación después”

1. La IA produce un plan de consulta estructurado (no respuesta final directa).
2. Se valida contra política SQL:
   - Solo `SELECT`.
   - Tablas permitidas: `facturas`, `facturas_proveedor`, `items`.
   - Límite de filas por defecto (`LIMIT`).
   - Bloqueo de funciones o comandos no permitidos.
3. Se ejecuta consulta.
4. Se genera interpretación desde resultados reales.

Resultado: se reduce el riesgo de respuestas inventadas.

## 5.2 Catálogo de preguntas críticas (hardening)

Implementar plantillas curadas para tus preguntas clave:

- “¿Qué se vendió ayer?”
- “¿Qué comprar a proveedor X?”
- “¿A qué proveedor comprar y qué productos?”
- “¿Qué productos se agotaron en 7 días?”

Estas rutas deben preferir SQL predefinido + parámetros, y usar LLM solo para redacción final.

## 5.3 Métricas de calidad

Definir y seguir semanalmente:

- `% respuestas correctas` en set de preguntas controladas.
- `latencia p50/p95` por pregunta.
- `% consultas bloqueadas por política`.
- `% respuestas sin datos`.

---

## 6) Modelo de datos analítico mínimo

Aunque el ETL ya actualiza diariamente, conviene agregar vistas para robustez:

- `vw_ventas_diarias`
- `vw_ventas_producto_periodo`
- `vw_compras_proveedor_periodo`
- `vw_stock_y_rotacion`
- `vw_sugerencia_compra_proveedor` (regla heurística inicial)

Beneficio: simplifica SQL generado por IA y mejora consistencia.

---

## 7) Plan de implementación por fases

## Fase 1 (Semana 1): Base técnica y seguridad

- Modularización mínima (separar UI/servicios/data).
- Política SQL robusta (allowlist + límites).
- Manejo central de errores y mensajes consistentes.
- Tests unitarios iniciales para validación SQL.

**Entregable:** arquitectura ordenada sin cambiar funcionalidad visible.

## Fase 2 (Semana 2): Fiabilidad en preguntas críticas

- Implementar rutas curadas para las 4 preguntas críticas.
- Añadir vistas SQL de soporte.
- Agregar validaciones de resultado (ej. no dataframe vacío sin explicación).

**Entregable:** respuestas más confiables para casos de negocio más importantes.

## Fase 3 (Semana 3): UX gerencial y rendimiento

- Mejoras de respuesta ejecutiva (insights + recomendaciones accionables).
- Caching de consultas frecuentes.
- Tiempos de respuesta y mensajes de estado más claros.

**Entregable:** experiencia más rápida y enfocada para gerente.

## Fase 4 (Semana 4): Operación en Railway

- Ajustes finales de despliegue y observabilidad básica.
- Dashboard técnico mínimo (errores, latencia, uso).
- Endurecimiento de fallback ante fallos de DB o API Gemini.

**Entregable:** operación estable en Railway.

---

## 8) Riesgos y mitigaciones

- **Riesgo:** SQL inválido o costoso generado por IA.
  - **Mitigación:** allowlist + límite + timeout + rutas curadas.

- **Riesgo:** Respuesta correcta en lenguaje pero incorrecta en dato.
  - **Mitigación:** explicación basada únicamente en resultados ejecutados.

- **Riesgo:** Cambios del ETL rompen consultas.
  - **Mitigación:** vistas estables y validación diaria de esquema.

- **Riesgo:** degradación por dependencia externa (Gemini).
  - **Mitigación:** reintentos controlados y mensajes de fallback claros.

---

## 9) Backlog priorizado (Impacto vs Esfuerzo)

## Alto impacto / bajo-medio esfuerzo

1. Política SQL estricta con allowlist.
2. Rutas curadas para preguntas críticas.
3. Separación de módulos principales.
4. Tests unitarios de seguridad SQL.

## Alto impacto / medio esfuerzo

5. Vistas analíticas en PostgreSQL.
6. Métricas de calidad automáticas.
7. Caching por intención y periodo.

## Medio impacto

8. Mejoras visuales de gráficos.
9. Plantillas de respuesta ejecutiva por tipo de consulta.

---

## 10) Definición de éxito (para tu caso)

Se considera éxito cuando, durante 2 semanas consecutivas:

- ≥ 90% de acierto en preguntas críticas.
- p95 de respuesta < 12 segundos.
- 0 incidentes de consultas peligrosas ejecutadas.
- Menos de 10% de respuestas “sin datos” en preguntas válidas.

---

## 11) Siguiente paso recomendado

Empezar por **Fase 1 + Fase 2** en una sola iteración corta, porque es donde se gana fiabilidad real sin sobrediseñar.

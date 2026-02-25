"""Consultas curadas para preguntas críticas del gerente."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CuratedQuery:
    key: str
    sql: str
    params: Dict[str, Any]
    explanation: str
    viz_hint: str


def _extract_provider_name(question: str) -> Optional[str]:
    # Ej: "¿qué le debo comprar a proveedor tecno sas?"
    m = re.search(r"proveedor\s+([\w\s\-\.]+)\??$", question, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def detect_curated_query(question: str) -> Optional[CuratedQuery]:
    q = question.lower().strip()

    if "que se vendio ayer" in q or "qué se vendió ayer" in q:
        return CuratedQuery(
            key="ventas_ayer",
            sql="""
                SELECT
                    nombre,
                    SUM(cantidad) AS cantidad_vendida,
                    SUM(total) AS total_vendido
                FROM facturas
                WHERE DATE(fecha) = CURRENT_DATE - INTERVAL '1 day'
                GROUP BY nombre
                ORDER BY total_vendido DESC
            """,
            params={},
            explanation="Ventas de ayer por producto, ordenadas por mayor facturación.",
            viz_hint="GRAFICO_BARRAS",
        )

    provider_name = _extract_provider_name(question)
    if provider_name and ("debo comprar" in q or "comprar" in q):
        return CuratedQuery(
            key="compras_proveedor",
            sql="""
                SELECT
                    nombre,
                    SUM(cantidad) AS cantidad_comprada_hist,
                    ROUND(AVG(precio)::numeric, 2) AS precio_promedio,
                    SUM(total) AS total_historico
                FROM facturas_proveedor
                WHERE proveedor ILIKE :provider
                GROUP BY nombre
                ORDER BY cantidad_comprada_hist DESC
            """,
            params={"provider": f"%{provider_name}%"},
            explanation=f"Histórico de compras al proveedor '{provider_name}'.",
            viz_hint="GRAFICO_BARRAS",
        )

    if "a que proveedor le debo comprar" in q or "a qué proveedor le debo comprar" in q:
        return CuratedQuery(
            key="sugerencia_proveedor_producto",
            sql="""
                WITH ultimos_precios AS (
                    SELECT
                        fp.nombre,
                        fp.proveedor,
                        fp.precio,
                        ROW_NUMBER() OVER (PARTITION BY fp.nombre ORDER BY fp.fecha DESC) AS rn
                    FROM facturas_proveedor fp
                ),
                stock_bajo AS (
                    SELECT i.nombre, i.cantidad_disponible
                    FROM items i
                    WHERE COALESCE(i.cantidad_disponible, 0) <= 2
                )
                SELECT
                    s.nombre,
                    s.cantidad_disponible,
                    u.proveedor,
                    u.precio AS ultimo_precio_compra
                FROM stock_bajo s
                LEFT JOIN ultimos_precios u ON u.nombre = s.nombre AND u.rn = 1
                ORDER BY s.cantidad_disponible ASC, s.nombre
            """,
            params={},
            explanation="Sugerencia de proveedor por producto con stock bajo usando el último precio registrado.",
            viz_hint="GRAFICO_BARRAS",
        )

    if "agotaron" in q and ("7 dias" in q or "7 días" in q):
        return CuratedQuery(
            key="agotados_ultimos_7_dias",
            sql="""
                SELECT
                    i.nombre,
                    COALESCE(i.cantidad_disponible, 0) AS stock_actual,
                    COALESCE(v.ventas_7d, 0) AS ventas_ultimos_7_dias
                FROM items i
                LEFT JOIN (
                    SELECT nombre, SUM(cantidad) AS ventas_7d
                    FROM facturas
                    WHERE DATE(fecha) >= CURRENT_DATE - INTERVAL '7 day'
                    GROUP BY nombre
                ) v ON v.nombre = i.nombre
                WHERE COALESCE(i.cantidad_disponible, 0) <= 0
                ORDER BY ventas_ultimos_7_dias DESC, i.nombre
            """,
            params={},
            explanation="Productos agotados hoy con contexto de ventas de los últimos 7 días.",
            viz_hint="GRAFICO_BARRAS",
        )

    return None

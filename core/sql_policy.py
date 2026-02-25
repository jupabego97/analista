"""Política de seguridad SQL para consultas de solo lectura."""
from __future__ import annotations

import re
from typing import Optional, Tuple

ALLOWED_TABLES = {"facturas", "facturas_proveedor", "items"}
DANGEROUS_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "CALL", "MERGE",
}


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql.strip()


def _extract_tables(sql: str) -> set[str]:
    pattern = r"\b(?:FROM|JOIN)\s+([a-zA-Z_][\w\.]*)"
    matches = re.findall(pattern, sql, flags=re.IGNORECASE)
    tables: set[str] = set()
    for match in matches:
        table = match.split(".")[-1].strip('"')
        tables.add(table.lower())
    return tables


def _extract_cte_names(sql: str) -> set[str]:
    ctes: set[str] = set()
    if not re.match(r"^\s*WITH\b", sql, flags=re.IGNORECASE):
        return ctes
    for name in re.findall(r"\b([a-zA-Z_][\w]*)\s+AS\s*\(", sql, flags=re.IGNORECASE):
        ctes.add(name.lower())
    return ctes


def validate_sql_query(sql: str) -> Tuple[bool, Optional[str]]:
    """Valida que la consulta sea segura y solo consulte tablas permitidas."""
    if not sql or not sql.strip():
        return False, "Consulta vacía"

    clean_sql = _strip_comments(sql)
    upper_sql = clean_sql.upper()

    if ";" in clean_sql.rstrip(";"):
        return False, "No se permiten múltiples sentencias SQL"

    starts_read_only = upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")
    if not starts_read_only:
        return False, "Solo se permiten consultas SELECT"

    for keyword in DANGEROUS_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            return False, f"Comando no permitido: {keyword}"

    tables = _extract_tables(clean_sql)
    cte_names = _extract_cte_names(clean_sql)
    not_allowed = [t for t in tables if t not in ALLOWED_TABLES and t not in cte_names]
    if not_allowed:
        return False, f"Tabla no permitida: {', '.join(sorted(not_allowed))}"

    return True, None


def enforce_default_limit(sql: str, default_limit: int = 200) -> str:
    """Añade LIMIT por defecto si la consulta no lo incluye."""
    clean_sql = _strip_comments(sql).rstrip(";")
    if re.search(r"\bLIMIT\b", clean_sql, flags=re.IGNORECASE):
        return clean_sql
    return f"{clean_sql}\nLIMIT {default_limit}"

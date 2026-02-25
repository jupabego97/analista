#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicación Analista de Negocio con IA
======================================

Aplicación Streamlit interactiva que permite hacer preguntas en lenguaje natural
sobre el negocio y recibe reportes completos con análisis, tablas y visualizaciones
automáticas, usando Gemini para interpretar las consultas.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

import streamlit as st

from core.sql_policy import enforce_default_limit, validate_sql_query
from services.curated_queries import detect_curated_query

# Cargar variables de entorno
load_dotenv()

# Configuración de página
st.set_page_config(
    page_title="Analista de Negocio con IA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes
DB_URL_ENV = "DATABASE_URL"
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"

# Intentar importar LangChain
try:
    from langchain_community.agent_toolkits import create_sql_agent, SQLDatabaseToolkit
    from langchain_community.utilities import SQLDatabase
    from langchain_community.callbacks import StreamlitCallbackHandler
    LANGCHAIN_COMMUNITY_AVAILABLE = True
except ImportError:
    try:
        from langchain.agents import create_sql_agent
        from langchain.sql_database import SQLDatabase
        from langchain.callbacks import StreamlitCallbackHandler
        from langchain.agents.agent_toolkits import SQLDatabaseToolkit
        LANGCHAIN_COMMUNITY_AVAILABLE = False
    except ImportError:
        LANGCHAIN_COMMUNITY_AVAILABLE = False
        LANGCHAIN_AVAILABLE = False

# Intentar importar Gemini
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        from langchain_community.llms import GooglePalm
        GEMINI_AVAILABLE = False
        GEMINI_LEGACY_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False
        GEMINI_LEGACY_AVAILABLE = False

# Intentar importar AgentType
try:
    from langchain.agents.agent_types import AgentType
except ImportError:
    AgentType = None

# ---------------------------------------------------------------------------
# Funciones de conexión y configuración
# ---------------------------------------------------------------------------

@st.cache_resource
def get_database_engine():
    """Crea el engine de SQLAlchemy para PostgreSQL con cache."""
    db_url = os.getenv(DB_URL_ENV)
    if not db_url:
        st.error(f"⚠️ Variable {DB_URL_ENV} no encontrada. Configura la URL de la base de datos en .env")
        st.stop()
    
    try:
        engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=300)
        # Probar conexión
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"❌ Error conectando a PostgreSQL: {e}")
        st.stop()

@st.cache_resource(ttl="2h")
def configure_sql_database(db_uri: str):
    """Configura SQLDatabase de LangChain para PostgreSQL."""
    try:
        return SQLDatabase.from_uri(database_uri=db_uri)
    except Exception as e:
        st.error(f"❌ Error configurando SQLDatabase: {e}")
        st.stop()

def get_gemini_api_key() -> Optional[str]:
    """Obtiene la API key de Gemini desde variables de entorno o session_state."""
    # Primero intentar desde variables de entorno
    api_key = os.getenv(GOOGLE_API_KEY_ENV) or os.getenv(GEMINI_API_KEY_ENV)
    
    # Si no está en env, intentar desde session_state (sidebar)
    if not api_key:
        api_key = st.session_state.get("gemini_api_key")
    
    return api_key

def create_system_prompt(db_schema: str = "") -> str:
    """Crea el prompt del sistema especializado para analista de negocio."""
    base_prompt = """Eres un analista de negocios experto en retail de tecnología en Colombia.

CONTEXTO DEL NEGOCIO:
- Empresa de retail de tecnología en Colombia
- Vende productos tecnológicos (computadores, portátiles, accesorios, etc.)
- Maneja inventario, ventas, compras a proveedores y análisis de rentabilidad

TABLAS PRINCIPALES DE LA BASE DE DATOS:

1. facturas: Ventas realizadas a clientes
   - Columnas: indx, id, item_id, fecha, hora, nombre, precio, cantidad, total, cliente, totalfact, metodo, vendedor
   - id: ID de la factura
   - fecha: Fecha de la venta
   - nombre: Nombre del producto vendido
   - precio: Precio unitario de venta
   - cantidad: Cantidad vendida
   - total: precio * cantidad
   - cliente: Nombre del cliente
   - totalfact: Total de la factura completa
   - metodo: Método de pago
   - vendedor: Nombre del vendedor

2. facturas_proveedor: Compras realizadas a proveedores
   - Columnas: id, fecha, nombre, precio, cantidad, total, total_fact, proveedor
   - id: ID de la factura de compra
   - fecha: Fecha de compra
   - nombre: Nombre del producto comprado
   - precio: Precio unitario de compra
   - cantidad: Cantidad comprada
   - total: precio * cantidad
   - proveedor: Nombre del proveedor

3. items: Inventario de productos
   - Columnas: id, nombre, familia, cantidad_disponible, precio_venta, etc.
   - nombre: Nombre del producto
   - familia: Categoría del producto
   - cantidad_disponible: Stock disponible

REGLAS ESTRICTAS:
- NUNCA ejecutes UPDATE, DELETE, DROP, INSERT, ALTER, TRUNCATE
- Solo usa SELECT para consultas
- Si la pregunta es ambigua, pregunta para aclarar antes de ejecutar
- Siempre valida que las columnas existan antes de usarlas
- Usa JOINs apropiados cuando necesites relacionar tablas
- Para fechas, usa formato DATE o TIMESTAMP según corresponda

FORMATO DE RESPUESTA:
1. Ejecuta la consulta SQL necesaria
2. Analiza los resultados obtenidos
3. Proporciona una interpretación clara en español
4. Identifica insights clave y patrones
5. Sugiere recomendaciones de negocio cuando sea relevante
6. Indica qué tipo de visualización sería útil (si aplica):
   - "GRAFICO_LINEA" para series temporales
   - "GRAFICO_BARRAS" para comparaciones categóricas
   - "GRAFICO_TORTA" para proporciones
   - "GRAFICO_SCATTER" para relaciones
   - "GRAFICO_HISTOGRAMA" para distribuciones
   - "TABLA" solo para datos tabulares

EJEMPLOS DE ANÁLISIS:
- Ventas por período: agrupa por fecha y suma totales
- Top productos: ordena por total vendido y toma los primeros N
- Análisis de clientes: agrupa por cliente y calcula métricas
- Rentabilidad: compara precio_venta (facturas) con precio_compra (facturas_proveedor)
- Tendencias: usa funciones de fecha para agrupar por mes, trimestre, etc.

IMPORTANTE:
- Siempre proporciona contexto y explicaciones claras
- Usa formato de moneda colombiana (COP) cuando muestres valores monetarios
- Sé específico con números y porcentajes
- Identifica oportunidades de mejora y riesgos"""
    
    if db_schema:
        base_prompt += f"\n\nESQUEMA DETALLADO DE LA BASE DE DATOS:\n{db_schema}"
    
    return base_prompt

def get_gemini_llm(api_key: str):
    """Crea y retorna una instancia de Gemini LLM."""
    if not GEMINI_AVAILABLE:
        st.error("❌ langchain-google-genai no está instalado. Instala con: pip install langchain-google-genai")
        st.stop()
    
    try:
        return ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=api_key,
            temperature=0,
            convert_system_message_to_human=True
        )
    except Exception as e:
        st.error(f"❌ Error creando instancia de Gemini: {e}")
        st.stop()

# ---------------------------------------------------------------------------
# Funciones de visualización automática
# ---------------------------------------------------------------------------

def detect_visualization_type(df: pd.DataFrame, query_context: str = "") -> str:
    """Detecta el tipo de visualización apropiada según los datos."""
    if df.empty:
        return "TABLA"
    
    # Detectar desde el contexto de la consulta
    query_lower = query_context.lower()
    
    if any(word in query_lower for word in ["temporal", "tiempo", "fecha", "mes", "día", "semana", "año", "tendencia", "evolución"]):
        if len(df.columns) >= 2:
            return "GRAFICO_LINEA"
    
    if any(word in query_lower for word in ["top", "mejor", "peor", "ranking", "comparar", "comparación"]):
        return "GRAFICO_BARRAS"
    
    if any(word in query_lower for word in ["proporción", "porcentaje", "distribución", "participación", "%"]):
        return "GRAFICO_TORTA"
    
    if any(word in query_lower for word in ["relación", "correlación", "scatter", "dispersión"]):
        if len(df.columns) >= 2:
            return "GRAFICO_SCATTER"
    
    if any(word in query_lower for word in ["distribución", "frecuencia", "histograma"]):
        return "GRAFICO_HISTOGRAMA"
    
    # Detectar por estructura de datos
    num_cols = len(df.columns)
    num_rows = len(df)
    
    # Si tiene columna de fecha y valores numéricos
    date_cols = [col for col in df.columns if any(word in str(col).lower() for word in ["fecha", "date", "mes", "año", "dia"])]
    if date_cols and num_cols >= 2:
        return "GRAFICO_LINEA"
    
    # Si tiene pocas filas y varias columnas numéricas, barras
    if num_rows <= 20 and num_cols >= 2:
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) >= 1:
            return "GRAFICO_BARRAS"
    
    # Si tiene una columna categórica y una numérica, torta o barras
    if num_cols == 2:
        return "GRAFICO_BARRAS"
    
    return "TABLA"

def create_visualization(df: pd.DataFrame, viz_type: str, title: str = "") -> Optional[go.Figure]:
    """Crea una visualización según el tipo especificado."""
    if df.empty:
        return None
    
    try:
        if viz_type == "GRAFICO_LINEA":
            # Buscar columna de fecha
            date_col = None
            for col in df.columns:
                if any(word in str(col).lower() for word in ["fecha", "date", "mes", "año", "dia", "periodo"]):
                    date_col = col
                    break
            
            if date_col:
                value_col = [c for c in df.columns if c != date_col][0]
                fig = px.line(df, x=date_col, y=value_col, title=title or "Evolución Temporal")
            else:
                # Usar índice como x
                value_col = df.select_dtypes(include=['number']).columns[0]
                fig = px.line(df, y=value_col, title=title or "Serie Temporal")
            return fig
        
        elif viz_type == "GRAFICO_BARRAS":
            # Identificar columnas categóricas y numéricas
            cat_col = None
            num_col = None
            
            for col in df.columns:
                if df[col].dtype == 'object' or df[col].dtype.name == 'category':
                    cat_col = col
                elif pd.api.types.is_numeric_dtype(df[col]):
                    num_col = col
            
            if cat_col and num_col:
                # Ordenar por valor numérico
                df_sorted = df.sort_values(by=num_col, ascending=False).head(20)
                fig = px.bar(df_sorted, x=cat_col, y=num_col, title=title or "Comparación")
            elif num_col:
                fig = px.bar(df, y=num_col, title=title or "Valores")
            else:
                return None
            return fig
        
        elif viz_type == "GRAFICO_TORTA":
            # Primera columna categórica, segunda numérica
            cat_col = df.columns[0]
            num_col = df.columns[1] if len(df.columns) > 1 else None
            
            if num_col and pd.api.types.is_numeric_dtype(df[num_col]):
                fig = px.pie(df, names=cat_col, values=num_col, title=title or "Distribución")
            else:
                # Contar frecuencias
                fig = px.pie(df, names=cat_col, title=title or "Distribución")
            return fig
        
        elif viz_type == "GRAFICO_SCATTER":
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) >= 2:
                fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], title=title or "Relación")
                return fig
            return None
        
        elif viz_type == "GRAFICO_HISTOGRAMA":
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                fig = px.histogram(df, x=numeric_cols[0], title=title or "Distribución")
                return fig
            return None
        
    except Exception as e:
        st.warning(f"⚠️ Error creando visualización: {e}")
        return None
    
    return None

# ---------------------------------------------------------------------------
# Funciones de análisis avanzado
# ---------------------------------------------------------------------------

def perform_advanced_analysis(df: pd.DataFrame, analysis_type: str) -> Dict[str, Any]:
    """Realiza análisis estadísticos avanzados según el tipo."""
    results = {}
    
    try:
        if analysis_type == "tendencias":
            # Análisis de tendencias temporales
            date_cols = [col for col in df.columns if any(word in str(col).lower() for word in ["fecha", "date"])]
            if date_cols:
                results["tendencia"] = "Análisis de tendencias temporal disponible"
        
        elif analysis_type == "segmentacion":
            # Análisis de segmentación
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                results["segmentacion"] = df.describe().to_dict()
        
        elif analysis_type == "correlaciones":
            # Análisis de correlaciones
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 1:
                results["correlaciones"] = df[numeric_cols].corr().to_dict()
        
        elif analysis_type == "kpis":
            # Cálculo de KPIs básicos
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                for col in numeric_cols:
                    results[f"kpi_{col}"] = {
                        "suma": float(df[col].sum()),
                        "promedio": float(df[col].mean()),
                        "mediana": float(df[col].median()),
                        "max": float(df[col].max()),
                        "min": float(df[col].min())
                    }
        
    except Exception as e:
        st.warning(f"⚠️ Error en análisis avanzado: {e}")
    
    return results

# ---------------------------------------------------------------------------
# Funciones de renderizado de respuestas
# ---------------------------------------------------------------------------

def extract_sql_from_response(response: str) -> Optional[str]:
    """Extrae la consulta SQL de la respuesta del agente."""
    # Buscar bloques de código SQL
    sql_pattern = r"```sql\s*(.*?)\s*```"
    matches = re.findall(sql_pattern, response, re.DOTALL | re.IGNORECASE)
    if matches:
        sql = matches[0].strip()
        # Validar que sea solo SELECT
        if sql.upper().strip().startswith("SELECT"):
            return sql
    
    # Buscar SELECT statements
    select_pattern = r"(SELECT\s+.*?;)"
    matches = re.findall(select_pattern, response, re.DOTALL | re.IGNORECASE)
    if matches:
        sql = matches[-1].strip()
        # Validar que sea solo SELECT
        if sql.upper().strip().startswith("SELECT"):
            return sql
    
    return None

def extract_visualization_hint(response: str) -> Optional[str]:
    """Extrae la sugerencia de visualización de la respuesta."""
    hints = ["GRAFICO_LINEA", "GRAFICO_BARRAS", "GRAFICO_TORTA", "GRAFICO_SCATTER", "GRAFICO_HISTOGRAMA"]
    for hint in hints:
        if hint in response:
            return hint
    return None



def execute_safe_query(db_engine, sql_query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Valida y ejecuta una consulta SQL segura de solo lectura."""
    is_valid, error_msg = validate_sql_query(sql_query)
    if not is_valid:
        raise ValueError(error_msg)

    safe_sql = enforce_default_limit(sql_query)
    with db_engine.connect() as conn:
        return pd.read_sql(text(safe_sql), conn, params=params or {})


def render_curated_response(query: str, db_engine):
    """Ejecuta consultas curadas para preguntas críticas y renderiza la respuesta."""
    curated = detect_curated_query(query)
    if not curated:
        return False

    st.markdown("### 📊 Análisis del Analista")
    st.markdown(f"**Consulta crítica detectada:** `{curated.key}`\n\n{curated.explanation}")

    try:
        df = execute_safe_query(db_engine, curated.sql, curated.params)
        if df.empty:
            st.info("No se encontraron datos para esta consulta crítica.")
            return True

        st.markdown("---")
        st.markdown("### 📋 Datos Obtenidos")
        st.dataframe(df, use_container_width=True)

        if st.session_state.get("auto_visualize", True):
            fig = create_visualization(df, curated.viz_hint, title=f"Análisis crítico: {query[:50]}...")
            if fig:
                st.markdown("---")
                st.markdown("### 📈 Visualización")
                st.plotly_chart(fig, use_container_width=True)

        st.session_state["last_query_results"] = df
        st.session_state["last_query"] = query
        return True
    except Exception as e:
        st.warning(f"⚠️ No se pudo ejecutar la consulta crítica: {e}")
        return True

def render_agent_response(response: str, query: str, db_engine):
    """Renderiza la respuesta del agente con texto, tablas y gráficos."""
    # Mostrar respuesta de texto
    st.markdown("### 📊 Análisis del Analista")
    st.markdown(response)
    
    # Intentar extraer y ejecutar SQL para obtener datos
    sql_query = extract_sql_from_response(response)
    if sql_query:
        try:
            df = execute_safe_query(db_engine, sql_query)
            
            if not df.empty:
                st.markdown("---")
                st.markdown("### 📋 Datos Obtenidos")
                
                # Mostrar tabla
                st.dataframe(df, use_container_width=True)
                
                # Detectar tipo de visualización
                viz_hint = extract_visualization_hint(response)
                if not viz_hint:
                    viz_hint = detect_visualization_type(df, query)
                
                # Crear visualización
                if viz_hint != "TABLA":
                    st.markdown("---")
                    st.markdown("### 📈 Visualización")
                    fig = create_visualization(df, viz_hint, title=f"Análisis: {query[:50]}...")
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                
                # Guardar datos en session_state para exportación
                st.session_state["last_query_results"] = df
                st.session_state["last_query"] = query
                
        except Exception as e:
            st.warning(f"⚠️ No se pudieron obtener datos para visualización: {e}")

# ---------------------------------------------------------------------------
# Interfaz principal
# ---------------------------------------------------------------------------

def render_sidebar():
    """Renderiza el sidebar con configuración y opciones."""
    with st.sidebar:
        st.title("⚙️ Configuración")
        
        # API Key de Gemini
        st.subheader("🔑 API Key de Gemini")
        api_key_env = get_gemini_api_key()
        
        if not api_key_env:
            st.warning("⚠️ API Key no configurada")
            api_key_input = st.text_input(
                "Ingresa tu GOOGLE_API_KEY:",
                type="password",
                help="Obtén tu API key en: https://makersuite.google.com/app/apikey"
            )
            if api_key_input:
                st.session_state["gemini_api_key"] = api_key_input
                st.success("✅ API Key guardada (solo para esta sesión)")
        else:
            st.success("✅ API Key configurada")
            if st.button("🔄 Cambiar API Key"):
                st.session_state["gemini_api_key"] = None
                st.rerun()
        
        st.markdown("---")
        
        # Información de la base de datos
        st.subheader("🗄️ Base de Datos")
        db_url = os.getenv(DB_URL_ENV)
        if db_url:
            st.success("✅ Conectado a PostgreSQL")
            # Ocultar credenciales
            db_display = db_url.split("@")[-1] if "@" in db_url else db_url[:50]
            st.caption(f"Host: {db_display}")
        else:
            st.error("❌ DATABASE_URL no configurada")
        
        st.markdown("---")
        
        # Ejemplos de preguntas
        st.subheader("💡 Ejemplos de Preguntas")
        example_questions = [
            "¿Cuáles son las ventas totales del último mes?",
            "¿Cuáles son los 10 productos más vendidos?",
            "¿Cuánto hemos vendido por cliente este año?",
            "¿Cuál es el margen de ganancia promedio por producto?",
            "¿Qué proveedores son los más importantes?",
            "¿Cuáles son las ventas por método de pago?",
            "¿Qué vendedor tiene mejor desempeño?",
            "¿Cuál es la tendencia de ventas mensuales?",
        ]
        
        for i, question in enumerate(example_questions):
            if st.button(f"📌 {question}", key=f"example_{i}", use_container_width=True):
                st.session_state["user_question"] = question
                st.rerun()
        
        st.markdown("---")
        
        # Opciones
        st.subheader("🔧 Opciones")
        st.session_state["show_sql"] = st.checkbox("Mostrar consultas SQL", value=False)
        st.session_state["auto_visualize"] = st.checkbox("Visualización automática", value=True)

def main():
    """Función principal de la aplicación."""
    st.title("🤖 Analista de Negocio con IA")
    st.markdown("Haz preguntas en lenguaje natural sobre tu negocio y recibe análisis completos con visualizaciones.")
    
    # Renderizar sidebar
    render_sidebar()
    
    # Verificar dependencias
    if not LANGCHAIN_COMMUNITY_AVAILABLE and not LANGCHAIN_AVAILABLE:
        st.error("""
        ❌ **Error: LangChain no está instalado**
        
        Instala las dependencias necesarias:
        ```bash
        pip install langchain langchain-community langchain-google-genai
        ```
        """)
        st.stop()
    
    if not GEMINI_AVAILABLE:
        st.error("""
        ❌ **Error: langchain-google-genai no está instalado**
        
        Instala con:
        ```bash
        pip install langchain-google-genai
        ```
        """)
        st.stop()
    
    # Verificar API key
    api_key = get_gemini_api_key()
    if not api_key:
        st.warning("""
        ⚠️ **Configura tu API Key de Gemini**
        
        Ve al sidebar y configura tu GOOGLE_API_KEY o GEMINI_API_KEY.
        Puedes obtenerla en: https://makersuite.google.com/app/apikey
        """)
        st.stop()
    
    # Inicializar conexión a BD
    try:
        db_engine = get_database_engine()
        db_url = os.getenv(DB_URL_ENV)
        db = configure_sql_database(db_url)
    except Exception as e:
        st.error(f"❌ Error conectando a la base de datos: {e}")
        st.stop()
    
    # Obtener esquema de la BD
    if "db_schema" not in st.session_state:
        try:
            with db_engine.connect() as conn:
                # Obtener información de tablas principales
                schema_query = """
                SELECT 
                    table_name,
                    column_name,
                    data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                    AND table_name IN ('facturas', 'facturas_proveedor', 'items')
                ORDER BY table_name, ordinal_position
                """
                schema_df = pd.read_sql(text(schema_query), conn)
                st.session_state["db_schema"] = schema_df.to_string()
        except Exception as e:
            st.warning(f"⚠️ No se pudo obtener el esquema: {e}")
            st.session_state["db_schema"] = ""
    
    # Configurar LLM
    try:
        llm = get_gemini_llm(api_key)
    except Exception as e:
        st.error(f"❌ Error configurando Gemini: {e}")
        st.stop()
    
    # Crear toolkit y agente
    try:
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        
        system_prompt = create_system_prompt(st.session_state.get("db_schema", ""))
        
        # Crear agente SQL
        if AgentType is not None:
            agent = create_sql_agent(
                llm=llm,
                toolkit=toolkit,
                verbose=st.session_state.get("show_sql", False),
                agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                system_message=system_prompt,
            )
        else:
            agent = create_sql_agent(
                llm=llm,
                toolkit=toolkit,
                verbose=st.session_state.get("show_sql", False),
                system_message=system_prompt,
            )
    except Exception as e:
        st.error(f"❌ Error creando agente SQL: {e}")
        st.info("Asegúrate de tener todas las dependencias instaladas correctamente.")
        st.stop()
    
    # Inicializar historial de conversación
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Mostrar historial de conversación
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "data" in message and message["data"] is not None:
                st.dataframe(message["data"], use_container_width=True)
            if "chart" in message and message["chart"] is not None:
                st.plotly_chart(message["chart"], use_container_width=True)
    
    # Input de pregunta
    question = st.chat_input("Haz una pregunta sobre tu negocio...")
    
    # Si hay pregunta desde ejemplo o input
    if "user_question" in st.session_state:
        question = st.session_state["user_question"]
        del st.session_state["user_question"]
    
    if question:
        # Agregar pregunta al historial
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        
        # Procesar pregunta: primero rutas curadas, luego agente LLM
        with st.chat_message("assistant"):
            with st.spinner("🤔 Analizando tu pregunta..."):
                try:
                    curated_handled = render_curated_response(question, db_engine)
                    if curated_handled:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "Consulta crítica resuelta con ruta curada y validación SQL."
                        })
                    else:
                        # Crear callback handler para Streamlit
                        callback_handler = StreamlitCallbackHandler(st.container())

                        # Ejecutar agente
                        response = agent.invoke(
                            {"input": question},
                            {"callbacks": [callback_handler]}
                        )

                        # Obtener respuesta
                        if isinstance(response, dict):
                            answer = response.get("output", str(response))
                        else:
                            answer = str(response)

                        # Renderizar respuesta
                        render_agent_response(answer, question, db_engine)

                        # Guardar en historial
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer
                        })

                except Exception as e:
                    error_msg = f"❌ Error procesando la pregunta: {e}"
                    st.error(error_msg)
                    
                    # Mensajes de error más específicos
                    error_str = str(e).lower()
                    if "connection" in error_str or "timeout" in error_str:
                        st.warning("⚠️ Error de conexión a la base de datos. Verifica tu conexión.")
                    elif "syntax" in error_str or "sql" in error_str:
                        st.info("""
                        **Error en la consulta SQL generada:**
                        - La pregunta puede ser demasiado compleja
                        - Intenta reformular la pregunta de manera más específica
                        - Verifica que menciones las tablas correctas (facturas, facturas_proveedor, items)
                        """)
                    elif "column" in error_str or "does not exist" in error_str:
                        st.info("""
                        **Error: Columna o tabla no encontrada:**
                        - Verifica que los nombres de columnas sean correctos
                        - Las tablas principales son: facturas, facturas_proveedor, items
                        - Revisa la ortografía de los nombres
                        """)
                    else:
                        st.info("""
                        **Sugerencias:**
                        - Verifica que la pregunta sea clara y específica
                        - Asegúrate de mencionar las tablas correctas (facturas, facturas_proveedor, items)
                        - Revisa que los nombres de columnas sean correctos
                        - Intenta simplificar la pregunta si es muy compleja
                        """)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
    
    # Opción de exportar últimos resultados
    if "last_query_results" in st.session_state:
        st.markdown("---")
        st.subheader("💾 Exportar Resultados")
        col1, col2 = st.columns(2)
        
        with col1:
            csv = st.session_state["last_query_results"].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"analisis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            try:
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    st.session_state["last_query_results"].to_excel(writer, index=False, sheet_name='Resultados')
                excel_data = output.getvalue()
                st.download_button(
                    label="📥 Descargar Excel",
                    data=excel_data,
                    file_name=f"analisis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.warning(f"⚠️ Error generando Excel: {e}")

if __name__ == "__main__":
    main()


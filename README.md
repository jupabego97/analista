# 🤖 Analista de Negocio con IA

Aplicación interactiva de análisis de negocio construida con Streamlit que permite hacer preguntas en lenguaje natural sobre tu negocio y recibir reportes completos con análisis, tablas y visualizaciones automáticas, utilizando Google Gemini para interpretar las consultas.

## ✨ Características

- **Preguntas en lenguaje natural**: Haz preguntas sobre tu negocio en español y recibe análisis completos
- **Análisis automático con IA**: Utiliza Google Gemini para interpretar consultas y generar análisis inteligentes
- **Visualizaciones automáticas**: Genera gráficos de líneas, barras, tortas, scatter plots e histogramas según el contexto
- **Rutas críticas curadas**: Preguntas clave del gerente (ventas de ayer, compras por proveedor, agotados 7 días) con SQL validado
- **Conexión a PostgreSQL**: Se conecta a tu base de datos PostgreSQL para análisis en tiempo real
- **Exportación de datos**: Descarga los resultados en formato CSV o Excel
- **Interfaz intuitiva**: Interfaz moderna y fácil de usar construida con Streamlit

## 📋 Requisitos Previos

- Python 3.8 o superior
- PostgreSQL (base de datos configurada)
- API Key de Google Gemini ([obtener aquí](https://makersuite.google.com/app/apikey))

## 🚀 Instalación

### Instalación Local

1. **Clona el repositorio**:
```bash
git clone https://github.com/jupabego97/analista.git
cd analista
```

2. **Crea un entorno virtual** (recomendado):
```bash
python -m venv venv

# En Windows:
venv\Scripts\activate

# En Linux/Mac:
source venv/bin/activate
```

3. **Instala las dependencias**:
```bash
pip install -r requirements.txt
```

4. **Configura las variables de entorno**:
   - Copia el archivo `env.example.txt` a `.env`:
   ```bash
   # En Windows:
   copy env.example.txt .env
   
   # En Linux/Mac:
   cp env.example.txt .env
   ```
   - Edita el archivo `.env` y configura:
     - `DATABASE_URL`: URL de conexión a tu base de datos PostgreSQL
     - `GOOGLE_API_KEY` o `GEMINI_API_KEY`: Tu API key de Google Gemini

### Despliegue en Railway

La aplicación está lista para desplegarse en Railway. Sigue estos pasos:

1. **Conecta tu repositorio de GitHub a Railway**:
   - Ve a [Railway Dashboard](https://railway.app/dashboard)
   - Crea un nuevo proyecto
   - Selecciona "Deploy from GitHub repo"
   - Conecta el repositorio `jupabego97/analista`

2. **Configura las variables de entorno en Railway**:
   - Ve a la pestaña **Variables** de tu servicio
   - Agrega:
     - `DATABASE_URL`: URL de tu base de datos PostgreSQL
     - `GOOGLE_API_KEY` o `GEMINI_API_KEY`: Tu API key de Google Gemini

3. **Railway detectará automáticamente**:
   - El `Procfile` con el comando de inicio
   - El `requirements.txt` para instalar dependencias
   - El `runtime.txt` para la versión de Python

4. **Genera un dominio público**:
   - Ve a **Settings** → **Generate Domain**
   - Railway creará una URL pública para tu aplicación

5. **¡Listo!** Tu aplicación estará disponible en la URL generada.

**Nota:** Railway usa automáticamente el puerto asignado a través de la variable `$PORT`. El `Procfile` ya está configurado para usar esta variable.

## 🗄️ Estructura de la Base de Datos

La aplicación está diseñada para trabajar con las siguientes tablas principales:

### Tabla: `facturas`
Ventas realizadas a clientes
- Columnas principales: `id`, `fecha`, `nombre`, `precio`, `cantidad`, `total`, `cliente`, `totalfact`, `metodo`, `vendedor`

### Tabla: `facturas_proveedor`
Compras realizadas a proveedores
- Columnas principales: `id`, `fecha`, `nombre`, `precio`, `cantidad`, `total`, `total_fact`, `proveedor`

### Tabla: `items`
Inventario de productos
- Columnas principales: `id`, `nombre`, `familia`, `cantidad_disponible`, `precio_venta`

## 🎯 Uso

1. **Inicia la aplicación**:
```bash
streamlit run app_analista_negocio.py
```

2. **Accede a la aplicación**:
   - La aplicación se abrirá automáticamente en tu navegador
   - Por defecto en: `http://localhost:8501`

3. **Configura tu API Key** (si no está en `.env`):
   - Ve al sidebar
   - Ingresa tu `GOOGLE_API_KEY` o `GEMINI_API_KEY`

4. **Haz preguntas sobre tu negocio**:
   - Escribe preguntas en lenguaje natural en el chat
   - O selecciona ejemplos de preguntas desde el sidebar
   - La IA analizará tu pregunta y generará un reporte completo

## 💡 Ejemplos de Preguntas

- "¿Cuáles son las ventas totales del último mes?"
- "¿Cuáles son los 10 productos más vendidos?"
- "¿Cuánto hemos vendido por cliente este año?"
- "¿Cuál es el margen de ganancia promedio por producto?"
- "¿Qué proveedores son los más importantes?"
- "¿Cuáles son las ventas por método de pago?"
- "¿Qué vendedor tiene mejor desempeño?"
- "¿Cuál es la tendencia de ventas mensuales?"

## 🔧 Configuración Avanzada

### Variables de Entorno

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| `DATABASE_URL` | URL de conexión a PostgreSQL | Sí |
| `GOOGLE_API_KEY` | API Key de Google Gemini | Sí |
| `GEMINI_API_KEY` | Alternativa a GOOGLE_API_KEY | No (si usas GOOGLE_API_KEY) |

### Opciones en la Interfaz

- **Mostrar consultas SQL**: Activa esta opción para ver las consultas SQL generadas
- **Visualización automática**: Desactiva si prefieres solo ver tablas

## 📊 Tipos de Visualizaciones

La aplicación detecta automáticamente el tipo de visualización más apropiada:

- **Gráfico de Líneas**: Para series temporales y tendencias
- **Gráfico de Barras**: Para comparaciones y rankings
- **Gráfico de Torta**: Para proporciones y distribuciones
- **Scatter Plot**: Para relaciones entre variables
- **Histograma**: Para distribuciones de frecuencia

## 🔒 Seguridad

- La aplicación **solo permite consultas SELECT** (lectura)
- Se valida que no se ejecuten comandos peligrosos (DROP, DELETE, UPDATE, INSERT, etc.)
- Se restringe el acceso a tablas permitidas (`facturas`, `facturas_proveedor`, `items`) y se aplica `LIMIT` por defecto
- Las credenciales se manejan mediante variables de entorno
- La API Key puede configurarse en `.env` o en la interfaz (solo para la sesión)

## 🛠️ Tecnologías Utilizadas

- **Streamlit**: Framework para aplicaciones web interactivas
- **LangChain**: Framework para aplicaciones con LLM
- **Google Gemini**: Modelo de lenguaje para análisis
- **PostgreSQL**: Base de datos relacional
- **SQLAlchemy**: ORM para Python
- **Plotly**: Librería de visualización interactiva
- **Pandas**: Manipulación y análisis de datos


## 🧭 Plan de Mejora Arquitectónica

Se añadió un plan técnico y de evolución del proyecto en `PLAN_MEJORA.md`, basado en enfoque de fiabilidad, seguridad SQL y operación en Railway.

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📧 Contacto

Para preguntas o sugerencias, abre un issue en el repositorio.

## 🙏 Agradecimientos

- Google Gemini por el modelo de lenguaje
- Streamlit por el framework de aplicaciones
- LangChain por las herramientas de integración con LLMs

